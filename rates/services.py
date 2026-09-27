"""Cotización persistida; la red se usa únicamente durante una sincronización."""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from config.exceptions import ExchangeRateUnavailable
from .models import RateQuote, RateSyncState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExchangeRate:
    value: Decimal
    source: str
    provider_updated_at: datetime | None = None
    age_seconds: int | None = None
    warning: str | None = None


def valid_rate(value):
    if isinstance(value, bool) or value is None or len(str(value)) > 64:
        raise ValueError("Invalid exchange rate")
    rate = Decimal(str(value))
    if not rate.is_finite() or not 0 < rate <= Decimal("1e12"):
        raise ValueError("Invalid exchange rate")
    # El almacenamiento tiene 16 decimales; evitar convertir tasas positivas en cero.
    if rate < Decimal("1e-16"):
        raise ValueError("Rate below supported precision")
    return rate


def get_exchange_rate():
    now = timezone.now()
    quote = RateQuote.objects.filter(pk=settings.LOCAL_CURRENCY).first()
    if quote:
        age = max(0, int((now - quote.provider_updated_at).total_seconds()))
        if age > settings.RATE_MAX_AGE_HOURS * 3600:
            raise ExchangeRateUnavailable("La última tasa conocida superó la antigüedad máxima permitida.")
        failed = RateSyncState.objects.filter(pk=quote.currency, failures__gt=0).exists()
        stale = failed or now >= quote.next_update_at
        return ExchangeRate(quote.value, "last_known" if stale else "stored", quote.provider_updated_at, age,
                            "Se utiliza la última tasa conocida; la actualización está pendiente." if stale else None)
    if settings.ALLOW_CONFIGURED_RATE_FALLBACK:
        try:
            return ExchangeRate(valid_rate(settings.DEFAULT_EXCHANGE_RATE), "fallback", warning=
                                "Se utilizó la tasa de respaldo configurada; no es una cotización actual.")
        except (ValueError, TypeError, InvalidOperation):
            pass
    raise ExchangeRateUnavailable()


def next_scheduled_refresh(now):
    local = now.astimezone(ZoneInfo(settings.RATE_SCHEDULE_TIMEZONE))
    for day in (0, 1):
        for hour in settings.RATE_SCHEDULE_HOURS:
            candidate = (local + timedelta(days=day)).replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate > local:
                return candidate.astimezone(dt_timezone.utc)


def provider_timestamp(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Invalid provider timestamp")
    return datetime.fromtimestamp(value, dt_timezone.utc)


def refresh_exchange_rate(force=False):
    now = timezone.now()
    currency = settings.LOCAL_CURRENCY
    with transaction.atomic():
        state, created = RateSyncState.objects.get_or_create(currency=currency)
        state = RateSyncState.objects.select_for_update().get(pk=currency)
        if state.lease_until and state.lease_until > now:
            return "busy"
        if not force and not created and state.next_attempt_at > now:
            return "not_due"
        lease = now + timedelta(minutes=2)
        state.lease_until, state.last_attempt_at = lease, now
        state.save(update_fields=["lease_until", "last_attempt_at"])
    # No bloquear una transacción de PostgreSQL mientras responde el proveedor.
    try:
        with requests.get(settings.EXCHANGE_RATE_API_URL, timeout=settings.EXCHANGE_RATE_TIMEOUT) as response:
            response.raise_for_status()
            payload = response.json(parse_float=Decimal)
        if not isinstance(payload, dict) or payload.get("result") != "success" or payload.get("base_code") != "USD":
            raise ValueError("Invalid provider response")
        value = valid_rate(payload["rates"][currency])
        updated = provider_timestamp(payload["time_last_update_unix"])
        next_update = provider_timestamp(payload["time_next_update_unix"])
        fetched = timezone.now()
        if updated > fetched + timedelta(minutes=5) or updated < fetched - timedelta(hours=settings.RATE_MAX_AGE_HOURS):
            raise ValueError("Invalid rate age")
        if next_update <= updated or next_update > updated + timedelta(days=2):
            raise ValueError("Invalid update interval")
        with transaction.atomic():
            state = RateSyncState.objects.select_for_update().get(pk=currency)
            if state.lease_until != lease:
                return "superseded"
            previous = RateQuote.objects.filter(pk=currency).first()
            if previous and updated < previous.provider_updated_at:
                raise ValueError("Provider returned an older quote")
            RateQuote.objects.update_or_create(currency=currency, defaults={"value": value,
                "provider_updated_at": updated, "fetched_at": fetched, "next_update_at": next_update})
            state.lease_until = None
            state.next_attempt_at = next_scheduled_refresh(fetched)
            state.last_success_at = fetched
            state.failures, state.last_error = 0, ""
            state.save()
        return "updated"
    except (requests.RequestException, ValueError, TypeError, KeyError, InvalidOperation, OverflowError, OSError):
        with transaction.atomic():
            state = RateSyncState.objects.select_for_update().get(pk=currency)
            if state.lease_until == lease:
                state.failures += 1
                delay = (1, 5, 15, 60)[min(state.failures - 1, 3)]
                state.next_attempt_at = timezone.now() + timedelta(minutes=delay)
                state.lease_until = None
                state.last_error = "Proveedor no disponible o respuesta inválida. Se conserva la tasa anterior."
                state.save()
        logger.warning("Rate refresh failed for %s; previous quote preserved", currency)
        raise ExchangeRateUnavailable("No se pudo actualizar la tasa; se conserva la última conocida.") from None
