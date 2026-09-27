from collections.abc import Mapping

from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from config.exceptions import ForbiddenInputFields

from .models import Book
from .validators import normalize_isbn, validate_country, validate_isbn


class ISBNField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(normalize_isbn(data))


class CountryField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data.strip().upper())


class BookSerializer(serializers.ModelSerializer):
    isbn = ISBNField(max_length=13, validators=[
        validate_isbn,
        UniqueValidator(queryset=Book.objects.all(), message="Ya existe un libro con este ISBN."),
    ])
    supplier_country = CountryField(max_length=2, validators=[validate_country])

    class Meta:
        model = Book
        fields = ["id", "title", "author", "isbn", "cost_usd", "selling_price_local",
                  "stock_quantity", "category", "supplier_country", "created_at", "updated_at"]
        read_only_fields = ["id", "selling_price_local", "created_at", "updated_at"]
        extra_kwargs = {"stock_quantity": {"required": True}}

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            read_only = set(data) & set(self.Meta.read_only_fields)
            errors = {key: ["Campo desconocido."] for key in sorted(unknown)}
            errors.update({key: ["Campo de solo lectura; lo establece el servidor."] for key in sorted(read_only)})
            if errors:
                raise ForbiddenInputFields(errors)
        return super().to_internal_value(data)

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError:
            # La restricción UNIQUE resuelve la carrera entre dos POST simultáneos.
            if Book.objects.filter(isbn=validated_data["isbn"]).exists():
                raise serializers.ValidationError({"isbn": ["Ya existe un libro con este ISBN."]})
            raise

    def update(self, instance, validated_data):
        if "cost_usd" in validated_data and validated_data["cost_usd"] != instance.cost_usd:
            validated_data["selling_price_local"] = None
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError:
            if Book.objects.filter(isbn=validated_data.get("isbn", instance.isbn)).exclude(pk=instance.pk).exists():
                raise serializers.ValidationError({"isbn": ["Ya existe un libro con este ISBN."]})
            raise


class PriceCalculationSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()
    cost_usd = serializers.DecimalField(max_digits=12, decimal_places=2)
    exchange_rate = serializers.CharField()
    cost_local = serializers.DecimalField(max_digits=18, decimal_places=2)
    margin_percentage = serializers.IntegerField()
    selling_price_local = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField()
    calculation_timestamp = serializers.DateTimeField()
    rate_source = serializers.ChoiceField(choices=["stored", "last_known", "fallback"])
    provider_updated_at = serializers.DateTimeField(allow_null=True)
    rate_age_seconds = serializers.IntegerField(allow_null=True)
    used_fallback = serializers.BooleanField()
    warning = serializers.CharField(allow_null=True)


class CategoryQuerySerializer(serializers.Serializer):
    category = serializers.CharField(max_length=100)


class BookListQuerySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    category = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    stock = serializers.ChoiceField(choices=["all", "low", "out"], default="all")


class InventoryOverviewSerializer(serializers.Serializer):
    total_titles = serializers.IntegerField()
    total_units = serializers.IntegerField()
    low_stock = serializers.IntegerField()
    out_of_stock = serializers.IntegerField()
    unpriced = serializers.IntegerField()
    low_stock_threshold = serializers.IntegerField()
    currency = serializers.CharField()
    categories = serializers.ListField(child=serializers.CharField())


class StockQuerySerializer(serializers.Serializer):
    threshold = serializers.IntegerField(min_value=0, max_value=2147483647, default=10)
