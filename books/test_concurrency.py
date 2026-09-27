from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event
from unittest.mock import patch

from django.db import close_old_connections, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

from .models import Book
from .services import ExchangeRate, calculate_book_price
from .test_api import book_data


class PriceConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_calculation_waits_for_locked_update_and_reads_committed_cost(self):
        book = Book.objects.create(**book_data(isbn="9788437604947"))
        rate_fetched = Event()

        def fetch():
            rate_fetched.set()
            return ExchangeRate(Decimal("0.85"), "stored")

        def calculate():
            close_old_connections()
            try:
                return calculate_book_price(book.pk)
            finally:
                connections.close_all()

        with patch("books.services.get_exchange_rate", side_effect=fetch), ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                locked = Book.objects.select_for_update().get(pk=book.pk)
                future = pool.submit(calculate)
                self.assertTrue(rate_fetched.wait(timeout=5), "El trabajador no inició la consulta")
                locked.cost_usd = Decimal("20.00")
                locked.save(update_fields=["cost_usd", "updated_at"])
            result = future.result(timeout=10)
        self.assertEqual(result["cost_usd"], Decimal("20.00"))
        self.assertEqual(result["selling_price_local"], Decimal("23.80"))
        book.refresh_from_db()
        self.assertEqual(book.selling_price_local, Decimal("23.80"))
