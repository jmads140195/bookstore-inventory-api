from django.contrib.auth import get_user_model
from accounts.models import UserAccess
from decimal import Decimal
from unittest.mock import patch

import requests
from django.db import OperationalError
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import Book
from .services import ExchangeRate


def book_data(**changes):
    data = {"title": "El Quijote", "author": "Miguel de Cervantes", "isbn": "978-84-376-0494-7",
            "cost_usd": "15.99", "stock_quantity": 25, "category": "Literatura Clásica", "supplier_country": "ES"}
    data.update(changes)
    return data


@override_settings(LOCAL_CURRENCY="EUR", DEFAULT_EXCHANGE_RATE="0.85")
class BookAPITests(APITestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="booktester")
        UserAccess.objects.create(user=user, role="full")
        self.client.force_authenticate(user)
        data = book_data(isbn="9788437604947")
        self.book = Book.objects.create(**data)

    def test_create_normalizes_isbn_and_country(self):
        response = self.client.post("/books", book_data(isbn="978-0-306-40615-7", supplier_country=" us "), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["isbn"], "9780306406157")
        self.assertEqual(response.data["supplier_country"], "US")
        self.assertIsNone(response.data["selling_price_local"])

    def test_duplicate_isbn_with_spaces_or_hyphens_returns_400(self):
        for isbn in ["9788437604947", "978-84-376-0494-7", "978 84 376 0494 7"]:
            with self.subTest(isbn=isbn):
                response = self.client.post("/books", book_data(isbn=isbn), format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn("isbn", response.data["error"]["details"])

    def test_invalid_inputs_return_400_without_creating_books(self):
        cases = [{"cost_usd": "0"}, {"cost_usd": "-1"}, {"cost_usd": "NaN"},
                 {"cost_usd": "1.999"}, {"stock_quantity": -1}, {"stock_quantity": 1.5},
                 {"isbn": "9780306406158"}, {"isbn": "123"}, {"isbn": 9780306406157},
                 {"supplier_country": "ZZ"}, {"title": "   "}, {"unexpected": "value"}]
        for changes in cases:
            with self.subTest(changes=changes):
                data = book_data(isbn="9780306406157")
                data.update(changes)
                response = self.client.post("/books", data, format="json")
                self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Book.objects.count(), 1)

    def test_valid_isbn_10_with_x_is_accepted(self):
        response = self.client.post("/books", book_data(isbn="0-8044-2957-x"), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["isbn"], "080442957X")

    def test_list_is_paginated_and_detail_is_accessible(self):
        response = self.client.get("/books")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.book.pk)
        self.assertEqual(self.client.get(f"/books/{self.book.pk}").status_code, 200)

    def test_pagination_has_second_page(self):
        for number in range(25):
            prefix = f"978{number:09d}"
            digit = (-sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(prefix))) % 10
            Book.objects.create(**book_data(isbn=prefix + str(digit)))
        response = self.client.get("/books")
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(len(self.client.get("/books?page=2").data["results"]), 6)

    def test_put_requires_complete_input_and_updates_book(self):
        url = f"/books/{self.book.pk}"
        self.assertEqual(self.client.put(url, {"title": "Otro"}, format="json").status_code, 400)
        response = self.client.put(url, book_data(title="Don Quijote", stock_quantity=30), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "Don Quijote")
        self.assertEqual(self.book.stock_quantity, 30)

    def test_cost_change_invalidates_calculated_price(self):
        self.book.selling_price_local = Decimal("19.03")
        self.book.save()
        response = self.client.patch(f"/books/{self.book.pk}", {"cost_usd": "20.00"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.book.refresh_from_db()
        self.assertIsNone(self.book.selling_price_local)

    def test_stock_change_preserves_price_and_clients_cannot_set_price(self):
        self.book.selling_price_local = Decimal("19.03")
        self.book.save()
        response = self.client.patch(f"/books/{self.book.pk}", {"stock_quantity": 0, "selling_price_local": "1.00"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.selling_price_local, Decimal("19.03"))
        self.assertEqual(self.book.stock_quantity, 0)

    def test_delete_then_detail_returns_404(self):
        url = f"/books/{self.book.pk}"
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_search_category_is_exact_case_insensitive(self):
        response = self.client.get("/books/search", {"category": "literatura Clásica"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(self.client.get("/books/search", {"category": "Clásica"}).data["count"], 0)
        self.assertEqual(self.client.get("/books/search").status_code, 400)

    def test_low_stock_is_strictly_less_than_threshold(self):
        self.book.stock_quantity = 10
        self.book.save()
        self.assertEqual(self.client.get("/books/low-stock").data["count"], 0)
        self.assertEqual(self.client.get("/books/low-stock?threshold=11").data["count"], 1)
        for value in ["-1", "abc", "1.5", "2147483648"]:
            self.assertEqual(self.client.get("/books/low-stock", {"threshold": value}).status_code, 400)

    @patch("books.services.get_exchange_rate", return_value=ExchangeRate(Decimal("0.85"), "stored"))
    def test_price_matches_pdf_and_is_persisted(self, rate):
        response = self.client.post(f"/books/{self.book.pk}/calculate-price")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["cost_local"], "13.59")
        self.assertEqual(response.data["selling_price_local"], "19.03")
        self.assertEqual(response.data["margin_percentage"], 40)
        self.assertFalse(response.data["used_fallback"])
        self.book.refresh_from_db()
        self.assertEqual(self.book.selling_price_local, Decimal("19.03"))

    @patch("books.services.get_exchange_rate", return_value=ExchangeRate(Decimal("0.45"), "stored"))
    def test_calculation_does_not_round_cost_before_applying_markup(self, rate):
        self.book.cost_usd = Decimal("0.01")
        self.book.save()
        response = self.client.post(f"/books/{self.book.pk}/calculate-price")
        self.assertEqual(response.data["cost_local"], "0.00")
        self.assertEqual(response.data["selling_price_local"], "0.01")

    @patch("rates.services.requests.get", side_effect=requests.Timeout)
    def test_missing_history_uses_fallback_without_network(self, request):
        response = self.client.post(f"/books/{self.book.pk}/calculate-price")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rate_source"], "fallback")
        self.assertTrue(response.data["used_fallback"])
        self.assertIsNotNone(response.data["warning"])
        request.assert_not_called()

    @override_settings(DEFAULT_EXCHANGE_RATE="")
    @patch("rates.services.requests.get", side_effect=requests.ConnectionError)
    def test_no_usable_rate_returns_503_without_changing_price(self, request):
        self.book.selling_price_local = Decimal("12.00")
        self.book.save()
        response = self.client.post(f"/books/{self.book.pk}/calculate-price")
        self.assertEqual(response.status_code, 503)
        self.book.refresh_from_db()
        self.assertEqual(self.book.selling_price_local, Decimal("12.00"))

    @patch("books.services.get_exchange_rate")
    def test_missing_book_never_calls_provider(self, rate):
        self.assertEqual(self.client.post("/books/999999/calculate-price").status_code, 404)
        rate.assert_not_called()

    @patch("books.services.get_exchange_rate")
    def test_cost_is_reread_after_loading_rate(self, rate):
        def fetch():
            Book.objects.filter(pk=self.book.pk).update(cost_usd=Decimal("20.00"))
            return ExchangeRate(Decimal("0.85"), "stored")
        rate.side_effect = fetch
        response = self.client.post(f"/books/{self.book.pk}/calculate-price")
        self.assertEqual(response.data["cost_usd"], "20.00")
        self.assertEqual(response.data["selling_price_local"], "23.80")

    @patch("books.services.get_exchange_rate", return_value=ExchangeRate(Decimal("1e12"), "stored"))
    def test_price_overflow_returns_503_without_saving(self, rate):
        self.book.cost_usd = Decimal("9999999999.99")
        self.book.save()
        response = self.client.post(f"/books/{self.book.pk}/calculate-price")
        self.assertEqual(response.status_code, 503)
        self.book.refresh_from_db()
        self.assertIsNone(self.book.selling_price_local)

    @patch("books.views.calculate_book_price", side_effect=RuntimeError("secret information"))
    def test_unexpected_error_returns_sanitized_500(self, calculate):
        response = self.client.post(f"/books/{self.book.pk}/calculate-price")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("secret information", str(response.data))

    @patch("books.views.calculate_book_price", side_effect=OperationalError("database password"))
    def test_database_failure_returns_sanitized_503(self, calculate):
        response = self.client.post(f"/books/{self.book.pk}/calculate-price")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("database password", str(response.data))

    def test_bad_json_and_unknown_route_have_errors(self):
        self.assertEqual(self.client.post("/books", "{bad", content_type="application/json").status_code, 400)
        response = self.client.get("/missing-route")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")
