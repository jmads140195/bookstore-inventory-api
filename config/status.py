from django.db import connection, OperationalError, InterfaceError
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .exceptions import error_payload


@require_GET
def home(request):
    return JsonResponse({"name": "Bookstore Inventory API", "app": "/app", "docs": "/docs", "health": "/health", "ready": "/ready", "books": "/books"})


@require_GET
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except (OperationalError, InterfaceError):
        return JsonResponse(error_payload("database_unavailable", "La base de datos no está disponible."), status=503)
    return JsonResponse({"status": "ok", "database": "ok"})
