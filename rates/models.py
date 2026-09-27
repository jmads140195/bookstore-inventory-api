from django.db import models
from django.utils import timezone


class RateQuote(models.Model):
    currency = models.CharField(max_length=3, primary_key=True)
    value = models.DecimalField(max_digits=30, decimal_places=16)
    provider_updated_at = models.DateTimeField()
    fetched_at = models.DateTimeField()
    next_update_at = models.DateTimeField()


class RateSyncState(models.Model):
    currency = models.CharField(max_length=3, primary_key=True)
    lease_until = models.DateTimeField(null=True)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    failures = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True)
    last_success_at = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=200, blank=True)
