from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .validators import validate_country, validate_isbn


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    # Guardamos el ISBN sin guiones. ISBN-10 puede terminar en X.
    isbn = models.CharField(
        max_length=13,
        unique=True,
        validators=[validate_isbn],
    )
    cost_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    selling_price_local = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=100)
    supplier_country = models.CharField(
        max_length=2,
        validators=[validate_country],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        # Estas restricciones también se aplican dentro de la base de datos.
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cost_usd__gt=0),
                name="book_cost_usd_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=0),
                name="book_stock_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(selling_price_local__isnull=True)
                    | models.Q(selling_price_local__gte=0)
                ),
                name="book_selling_price_nonnegative",
            ),
        ]

    def __str__(self):
        return self.title
