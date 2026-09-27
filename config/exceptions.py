import logging

from django.db import OperationalError, InterfaceError
from django.http import JsonResponse
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ExchangeRateUnavailable(APIException):
    status_code = 503
    default_detail = "No hay una tasa de cambio válida ni una tasa de respaldo configurada."
    default_code = "exchange_rate_unavailable"


def error_payload(code, message, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(exc, ValidationError):
            response.data = error_payload("validation_error", "Datos inválidos.", response.data)
        else:
            message = str(response.data.get("detail", "No se pudo procesar la petición."))
            response.data = error_payload(getattr(exc, "default_code", "request_error"), message)
        return response
    if isinstance(exc, (OperationalError, InterfaceError)):
        logger.exception("Database unavailable")
        return Response(error_payload("database_unavailable", "La base de datos no está disponible."), status=503)
    logger.exception("Unhandled API error")
    return Response(error_payload("internal_error", "Ocurrió un error interno."), status=500)


def not_found(request, exception=None):
    return JsonResponse(error_payload("not_found", "Ruta no encontrada."), status=404)


def server_error(request):
    return JsonResponse(error_payload("internal_error", "Ocurrió un error interno."), status=500)
