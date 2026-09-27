"""Integración externa y reglas de precios, separadas de la capa HTTP."""
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

import requests
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from config.exceptions import ExchangeRateUnavailable
from .models import Book

logger = logging.getLogger(__name__)
MARGIN_PERCENTAGE = 40
CENT = Decimal("0.01")
MAX_PRICE = Decimal("9999999999999999.99")


@dataclass(frozen=True)
class ExchangeRate:
    value: Decimal
    source: str


def valid_rate(value):
    if isinstance(value, bool) or value is None or len(str(value)) > 64:
        raise ValueError("Invalid exchange rate")
    rate = Decimal(str(value))
    if not rate.is_finite() or not 0 < rate <= Decimal("1e12"):
        raise ValueError("Invalid exchange rate")
    return rate


def get_exchange_rate():
    try:
        with requests.get(settings.EXCHANGE_RATE_API_URL, timeout=settings.EXCHANGE_RATE_TIMEOUT) as response:
            response.raise_for_status()
            payload = response.json(parse_float=Decimal)
        if not isinstance(payload, dict) or payload.get("base") != "USD":
            raise ValueError("Unexpected exchange-rate base")
        rate = valid_rate(payload["rates"][settings.LOCAL_CURRENCY])
        return ExchangeRate(rate, "api")
    except (requests.RequestException, ValueError, TypeError, KeyError, InvalidOperation):
        logger.warning("Exchange-rate provider unavailable or invalid; evaluating configured fallback")
        try:
            rate = valid_rate(settings.DEFAULT_EXCHANGE_RATE)
        except (ValueError, TypeError, InvalidOperation):
            raise ExchangeRateUnavailable() from None
        return ExchangeRate(rate, "fallback")


def calculate_book_price(book_id):
    # La llamada de red se hace antes de tomar el bloqueo de la fila.
    rate = get_exchange_rate()
    with transaction.atomic():
        book = get_object_or_404(Book.objects.select_for_update(), pk=book_id)
        with localcontext() as context:
            context.prec = 50
            cost_local = book.cost_usd * rate.value
            multiplier = Decimal("1") + Decimal(MARGIN_PERCENTAGE) / Decimal("100")
            selling_price = (cost_local * multiplier).quantize(CENT, rounding=ROUND_HALF_UP)
            if selling_price > MAX_PRICE:
                raise ExchangeRateUnavailable("El precio calculado supera la capacidad del campo monetario.")
            shown_cost = cost_local.quantize(CENT, rounding=ROUND_HALF_UP)
        book.selling_price_local = selling_price
        book.save(update_fields=["selling_price_local", "updated_at"])
        used_fallback = rate.source == "fallback"
        return {
            "book_id": book.pk,
            "cost_usd": book.cost_usd,
            "exchange_rate": str(rate.value),
            "cost_local": shown_cost,
            "margin_percentage": MARGIN_PERCENTAGE,
            "selling_price_local": selling_price,
            "currency": settings.LOCAL_CURRENCY,
            "calculation_timestamp": timezone.now(),
            "rate_source": rate.source,
            "used_fallback": used_fallback,
            "warning": "Se utilizó la tasa de respaldo configurada; no es una cotización actual." if used_fallback else None,
        }
