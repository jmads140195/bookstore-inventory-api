from io import BytesIO

from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework.parsers import JSONParser


class PayloadTooLarge(APIException):
    status_code = 413
    default_detail = "El JSON supera el tamaño máximo permitido."
    default_code = "payload_too_large"


class BoundedJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        data = stream.read(settings.API_MAX_JSON_BYTES + 1)
        if len(data) > settings.API_MAX_JSON_BYTES:
            raise PayloadTooLarge()
        return super().parse(BytesIO(data), media_type=media_type, parser_context=parser_context)
