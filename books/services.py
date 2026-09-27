"""Integración externa y reglas de precios, separadas de la capa HTTP."""
from decimal import Decimal, ROUND_HALF_UP, localcontext

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from config.exceptions import ExchangeRateUnavailable
from rates.services import ExchangeRate, get_exchange_rate
from .models import Book

MARGIN_PERCENTAGE = 40
CENT = Decimal("0.01")
MAX_PRICE = Decimal("9999999999999999.99")


def calculate_book_price(book_id):
    # Lee la tasa persistida: nunca consulta la red durante un cálculo.
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
            "provider_updated_at": rate.provider_updated_at,
            "rate_age_seconds": rate.age_seconds,
            "warning": rate.warning,
        }
