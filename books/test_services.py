from decimal import Decimal
from unittest.mock import patch

import requests
from django.test import SimpleTestCase, override_settings

from config.exceptions import ExchangeRateUnavailable
from .services import get_exchange_rate


@override_settings(LOCAL_CURRENCY="EUR", DEFAULT_EXCHANGE_RATE="0.85")
class ExchangeRateTests(SimpleTestCase):
    @patch("books.services.requests.get")
    def test_valid_response_and_bounded_timeout(self, get):
        response = get.return_value.__enter__.return_value
        response.json.return_value = {"base": "USD", "rates": {"EUR": Decimal("0.91")}}
        quote = get_exchange_rate()
        self.assertEqual(quote.value, Decimal("0.91"))
        self.assertEqual(quote.source, "api")
        self.assertEqual(get.call_args.kwargs["timeout"], (3.05, 5))

    @patch("books.services.requests.get")
    def test_invalid_provider_payloads_use_fallback(self, get):
        response = get.return_value.__enter__.return_value
        cases = [None, [], {}, {"base": "EUR", "rates": {"EUR": 1}},
                 {"base": "USD", "rates": {}}, {"base": "USD", "rates": None}]
        cases += [{"base": "USD", "rates": {"EUR": value}} for value in [0, -1, True, "NaN", "Infinity", "oops", "1e100", None]]
        for payload in cases:
            with self.subTest(payload=payload):
                response.json.return_value = payload
                self.assertEqual(get_exchange_rate().source, "fallback")

    @patch("books.services.requests.get")
    def test_http_error_and_invalid_json_use_fallback(self, get):
        response = get.return_value.__enter__.return_value
        response.raise_for_status.side_effect = requests.HTTPError("503")
        self.assertEqual(get_exchange_rate().source, "fallback")
        response.raise_for_status.side_effect = None
        response.json.side_effect = ValueError("invalid JSON")
        self.assertEqual(get_exchange_rate().source, "fallback")

    @patch("books.services.requests.get", side_effect=requests.Timeout)
    def test_invalid_fallback_values_raise_unavailable(self, get):
        for value in ["", "0", "-1", "NaN", "Infinity", "abc"]:
            with self.subTest(value=value), override_settings(DEFAULT_EXCHANGE_RATE=value):
                with self.assertRaises(ExchangeRateUnavailable):
                    get_exchange_rate()
