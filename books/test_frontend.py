from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import UserAccess
from .models import Book
from .test_api import book_data


class InventoryFrontendTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="reader")
        UserAccess.objects.create(user=self.user, role="basic")
        self.book = Book.objects.create(**book_data(isbn="9788437604947"))

    @override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
    def test_public_login_page_does_not_grant_access_to_inventory(self):
        response = self.client.get("/app")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tu siguiente capítulo.")
        self.assertContains(response, "/static/books/ui.js")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("script-src 'self'", response["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertNotContains(response, self.book.title)
        self.assertEqual(self.client.get("/books").status_code, 401)
        self.assertEqual(self.client.get("/books/overview").status_code, 401)

    def test_summary_is_global_and_accessible_to_basic_users(self):
        self.client.force_authenticate(self.user)
        Book.objects.create(**book_data(isbn="9780306406157", category="Ciencia", stock_quantity=3))
        Book.objects.create(**book_data(isbn="9780140328721", category="Infantil", stock_quantity=0,
                                       selling_price_local=Decimal("10.00")))
        result = self.client.get("/books/overview?q=NoExiste&stock=out")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["total_titles"], 3)
        self.assertEqual(result.data["total_units"], 28)
        self.assertEqual(result.data["low_stock"], 2)
        self.assertEqual(result.data["out_of_stock"], 1)
        self.assertEqual(result.data["unpriced"], 2)
        self.assertEqual(result.data["low_stock_threshold"], 10)
        self.assertEqual(set(result.data["categories"]), {"Literatura Clásica", "Ciencia", "Infantil"})
        self.assertEqual(self.client.post("/books/overview", {}, format="json").status_code, 403)

    def test_filters_search_across_inventory_and_combine(self):
        self.client.force_authenticate(self.user)
        space = Book.objects.create(**book_data(isbn="9780306406157", title="Espacio", author="Isaac",
                                              category="Ciencia", stock_quantity=3))
        empty = Book.objects.create(**book_data(isbn="9780140328721", title="Matilda", category="Infantil", stock_quantity=0))
        for query, ids in [({"q": "espacio"}, [space.id]), ({"q": "ISAAC"}, [space.id]),
                           ({"q": "978-0-306-40615-7"}, [space.id]),
                           ({"q": "isaac", "category": "ciencia", "stock": "low"}, [space.id]),
                           ({"stock": "low"}, [space.id, empty.id]), ({"stock": "out"}, [empty.id]),
                           ({"q": "Isaac", "category": "Infantil"}, []), ({"q": "---"}, [])]:
            with self.subTest(query=query):
                response = self.client.get("/books", query)
                self.assertEqual(response.status_code, 200)
                self.assertEqual([book["id"] for book in response.data["results"]], ids)
        self.assertEqual(self.client.get("/books").data["count"], 3)

    def test_invalid_filter_does_not_change_records(self):
        self.client.force_authenticate(self.user)
        for query in [{"q": "x" * 151}, {"category": "x" * 101}, {"stock": "negative"}]:
            self.assertEqual(self.client.get("/books", query).status_code, 400)
        self.assertEqual(Book.objects.count(), 1)

    def test_empty_inventory_summary_is_zero(self):
        self.client.force_authenticate(self.user)
        self.book.delete()
        response = self.client.get("/books/overview")
        self.assertEqual(response.status_code, 200)
        for field in ["total_titles", "total_units", "low_stock", "out_of_stock", "unpriced"]:
            self.assertEqual(response.data[field], 0)
        self.assertEqual(response.data["categories"], [])
