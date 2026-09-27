from django.contrib import admin
from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "isbn", "stock_quantity", "cost_usd", "selling_price_local"]
    search_fields = ["title", "author", "isbn"]
    list_filter = ["category", "supplier_country"]
    readonly_fields = ["selling_price_local", "created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        if change and "cost_usd" in form.changed_data:
            obj.selling_price_local = None
        super().save_model(request, obj, form, change)
