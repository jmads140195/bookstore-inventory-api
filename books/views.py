from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.permissions import InventoryAccess

from .models import Book
from .serializers import BookSerializer, CategoryQuerySerializer, PriceCalculationSerializer, StockQuerySerializer
from .services import calculate_book_price


class BookViewSet(viewsets.ModelViewSet):
    permission_classes = [InventoryAccess]
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    lookup_value_regex = "[0-9]+"

    def update(self, request, *args, **kwargs):
        # Serializa cambios sobre el mismo libro en PostgreSQL, incluido su precio.
        with transaction.atomic():
            instance = get_object_or_404(self.get_queryset().select_for_update(), pk=kwargs["pk"])
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop("partial", False))
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @extend_schema(parameters=[CategoryQuerySerializer], responses=BookSerializer(many=True))
    @action(detail=False, methods=["get"])
    def search(self, request):
        query = CategoryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        books = self.get_queryset().filter(category__iexact=query.validated_data["category"])
        page = self.paginate_queryset(books)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @extend_schema(parameters=[StockQuerySerializer], responses=BookSerializer(many=True))
    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        query = StockQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        books = self.get_queryset().filter(stock_quantity__lt=query.validated_data["threshold"])
        page = self.paginate_queryset(books)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @extend_schema(request=None, responses={200: PriceCalculationSerializer})
    @action(detail=True, methods=["post"], url_path="calculate-price", pagination_class=None)
    def calculate_price(self, request, pk=None):
        book = self.get_object()  # Un ID inexistente devuelve 404 sin consultar al proveedor.
        result = calculate_book_price(book.pk)
        return Response(PriceCalculationSerializer(result).data)
