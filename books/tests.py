from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Book


class BookModelTests(TestCase):
    def make_book(self, **changes):
        data = {
            "title": "El Quijote",
            "author": "Miguel de Cervantes",
            "isbn": "9788437604947",
            "cost_usd": Decimal("15.99"),
            "stock_quantity": 25,
            "category": "Literatura Clásica",
            "supplier_country": "ES",
        }
        data.update(changes)
        return Book(**data)

    def test_book_can_be_saved_without_a_calculated_price(self):
        book = self.make_book(stock_quantity=0)
        book.full_clean()
        book.save()
        saved = Book.objects.get(pk=book.pk)
        self.assertEqual(saved.cost_usd, Decimal("15.99"))
        self.assertEqual(saved.stock_quantity, 0)
        self.assertIsNone(saved.selling_price_local)

    def test_invalid_business_values_fail_validation(self):
        cases = [
            ("cost_usd", Decimal("0.00")),
            ("cost_usd", Decimal("-1.00")),
            ("stock_quantity", -1),
            ("selling_price_local", Decimal("-1.00")),
            ("isbn", "123"),
            ("isbn", "abcdefghijklm"),
            ("supplier_country", "Spain"),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValidationError) as error:
                    self.make_book(**{field: value}).full_clean()
                self.assertIn(field, error.exception.message_dict)

    def test_duplicate_isbn_fails_validation(self):
        self.make_book().save()
        with self.assertRaises(ValidationError) as error:
            self.make_book(title="Otro título").full_clean()
        self.assertIn("isbn", error.exception.message_dict)

    def test_database_rejects_duplicate_isbn_even_without_full_clean(self):
        self.make_book().save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_book(title="Otro título").save()

    def test_database_rejects_invalid_amounts_even_without_full_clean(self):
        cases = [
            {"cost_usd": Decimal("0.00")},
            {"cost_usd": Decimal("-1.00")},
            {"stock_quantity": -1},
            {"selling_price_local": Decimal("-1.00")},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.make_book(**changes).save()
