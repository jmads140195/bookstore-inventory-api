from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import FullAccess
from accounts.throttles import RefreshRateThrottle, UserThrottle
from .serializers import RateSerializer, RefreshSerializer
from .services import get_exchange_rate, refresh_exchange_rate


class CurrentRateView(APIView):
    @extend_schema(responses=RateSerializer)
    def get(self, request):
        rate = get_exchange_rate()
        return Response(RateSerializer({"base_currency": "USD", "currency": settings.LOCAL_CURRENCY,
            "exchange_rate": str(rate.value), "rate_source": rate.source,
            "provider_updated_at": rate.provider_updated_at, "rate_age_seconds": rate.age_seconds,
            "warning": rate.warning}).data)


class RefreshRateView(APIView):
    permission_classes = [FullAccess]
    throttle_classes = [UserThrottle, RefreshRateThrottle]

    @extend_schema(request=None, responses=RefreshSerializer)
    def post(self, request):
        return Response({"status": refresh_exchange_rate(force=True)})
