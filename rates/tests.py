from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import UserAccess
from config.exceptions import ExchangeRateUnavailable
from .models import RateQuote, RateSyncState
from .services import get_exchange_rate, next_scheduled_refresh, refresh_exchange_rate


@override_settings(LOCAL_CURRENCY="EUR", DEFAULT_EXCHANGE_RATE="0.85", RATE_MAX_AGE_HOURS=48)
class RateTests(APITestCase):
    def quote(self, **changes):
        now = timezone.now().replace(microsecond=0)
        values = {"currency": "EUR", "value": Decimal("0.91"), "provider_updated_at": now - timedelta(hours=1),
                  "fetched_at": now, "next_update_at": now + timedelta(hours=23)}
        values.update(changes)
        return RateQuote.objects.create(**values)

    def payload(self, **changes):
        now = timezone.now().replace(microsecond=0)
        values = {"result": "success", "base_code": "USD", "rates": {"EUR": Decimal("0.92")},
                  "time_last_update_unix": int(now.timestamp()),
                  "time_next_update_unix": int((now + timedelta(days=1)).timestamp())}
        values.update(changes)
        return values

    @patch("rates.services.requests.get")
    def test_reads_persisted_rate_without_network(self, get):
        self.quote()
        rate = get_exchange_rate()
        self.assertEqual(rate.value, Decimal("0.91"))
        self.assertEqual(rate.source, "stored")
        self.assertGreaterEqual(rate.age_seconds, 3600)
        get.assert_not_called()

    @patch("rates.services.requests.get", side_effect=requests.Timeout)
    def test_provider_failure_preserves_last_known_rate_and_retries(self, get):
        quote = self.quote()
        with self.assertRaises(ExchangeRateUnavailable):
            refresh_exchange_rate(force=True)
        quote.refresh_from_db()
        self.assertEqual(quote.value, Decimal("0.91"))
        self.assertEqual(get_exchange_rate().source, "last_known")
        state = RateSyncState.objects.get(pk="EUR")
        self.assertEqual(state.failures, 1)
        self.assertIsNone(state.lease_until)
        self.assertLessEqual(state.next_attempt_at - timezone.now(), timedelta(minutes=1))
        self.assertEqual(refresh_exchange_rate(), "not_due")
        self.assertEqual(get.call_count, 1)

    def test_expired_rate_is_rejected_even_with_configured_fallback(self):
        self.quote(provider_updated_at=timezone.now() - timedelta(hours=49))
        with self.assertRaises(ExchangeRateUnavailable):
            get_exchange_rate()

    def test_pending_publication_is_marked_last_known(self):
        self.quote(provider_updated_at=timezone.now() - timedelta(hours=25), next_update_at=timezone.now() - timedelta(hours=1))
        rate = get_exchange_rate()
        self.assertEqual(rate.source, "last_known")
        self.assertIsNotNone(rate.warning)

    def test_fallback_only_when_no_history_and_can_be_disabled(self):
        self.assertEqual(get_exchange_rate().source, "fallback")
        with override_settings(ALLOW_CONFIGURED_RATE_FALLBACK=False), self.assertRaises(ExchangeRateUnavailable):
            get_exchange_rate()
        for value in ["", "0", "-1", "NaN", "Infinity", "abc", "1e100", "1e-100"]:
            with self.subTest(value=value), override_settings(DEFAULT_EXCHANGE_RATE=value), self.assertRaises(ExchangeRateUnavailable):
                get_exchange_rate()

    @patch("rates.services.requests.get")
    def test_refresh_persists_provider_time_and_shared_schedule(self, get):
        get.return_value.__enter__.return_value.json.return_value = self.payload()
        self.assertEqual(refresh_exchange_rate(), "updated")
        self.assertEqual(RateQuote.objects.get(pk="EUR").value, Decimal("0.92"))
        self.assertEqual(get_exchange_rate().source, "stored")
        self.assertEqual(refresh_exchange_rate(), "not_due")
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs["timeout"], settings.EXCHANGE_RATE_TIMEOUT)

    @patch("rates.services.requests.get")
    def test_invalid_payloads_never_replace_saved_rate(self, get):
        self.quote()
        response = get.return_value.__enter__.return_value
        cases = [None, [], {}, self.payload(base_code="EUR"), self.payload(result="error"),
                 self.payload(rates={}), self.payload(time_last_update_unix=True),
                 self.payload(time_last_update_unix=1), self.payload(time_next_update_unix=1),
                 self.payload(time_last_update_unix=10**30)]
        cases += [self.payload(rates={"EUR": v}) for v in [0, -1, True, "NaN", "Infinity", "oops", "1e100", None]]
        for payload in cases:
            with self.subTest(payload=payload):
                response.json.return_value = payload
                with self.assertRaises(ExchangeRateUnavailable):
                    refresh_exchange_rate(force=True)
                self.assertEqual(RateQuote.objects.get(pk="EUR").value, Decimal("0.91"))

    @patch("rates.services.requests.get")
    def test_active_lease_prevents_duplicate_provider_request(self, get):
        RateSyncState.objects.create(currency="EUR", lease_until=timezone.now() + timedelta(minutes=1))
        self.assertEqual(refresh_exchange_rate(force=True), "busy")
        get.assert_not_called()

    @patch("rates.services.requests.get")
    def test_older_provider_response_does_not_replace_newer_quote(self, get):
        self.quote(provider_updated_at=timezone.now())
        get.return_value.__enter__.return_value.json.return_value = self.payload(
            time_last_update_unix=int((timezone.now() - timedelta(hours=1)).timestamp()))
        with self.assertRaises(ExchangeRateUnavailable):
            refresh_exchange_rate(force=True)
        self.assertEqual(RateQuote.objects.get(pk="EUR").value, Decimal("0.91"))

    def test_schedule_is_8_and_15_in_caracas(self):
        for hour, expected_hour, expected_day in [(11, 12, 1), (12, 19, 1), (18, 19, 1), (19, 12, 2), (23, 12, 2)]:
            now = datetime(2026, 9, 1, hour, tzinfo=dt_timezone.utc)
            expected = datetime(2026, 9, expected_day, expected_hour, tzinfo=dt_timezone.utc)
            self.assertEqual(next_scheduled_refresh(now), expected)

    @patch("rates.views.refresh_exchange_rate", return_value="updated")
    def test_rate_read_and_refresh_permissions_and_limit(self, refresh):
        user = get_user_model().objects.create_user(username="rate-user")
        self.assertEqual(self.client.get("/rates/current").status_code, 401)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/rates/current").status_code, 200)
        self.assertEqual(self.client.post("/rates/refresh").status_code, 403)
        UserAccess.objects.create(user=user, role="full")
        self.assertEqual(self.client.post("/rates/refresh").status_code, 200)
        self.assertEqual(self.client.post("/rates/refresh").status_code, 429)
        refresh.assert_called_once()
