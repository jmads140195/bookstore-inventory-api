from rest_framework import serializers


class RateSerializer(serializers.Serializer):
    base_currency = serializers.CharField()
    currency = serializers.CharField()
    exchange_rate = serializers.CharField()
    rate_source = serializers.ChoiceField(choices=["stored", "last_known", "fallback"])
    provider_updated_at = serializers.DateTimeField(allow_null=True)
    rate_age_seconds = serializers.IntegerField(allow_null=True)
    warning = serializers.CharField(allow_null=True)


class RefreshSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["updated", "busy", "not_due", "superseded"])
