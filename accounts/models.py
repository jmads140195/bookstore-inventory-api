from django.db import models
from django.conf import settings


class UserAccess(models.Model):
    class Role(models.TextChoices):
        BASIC = "basic", "Básico"
        FULL = "full", "Completo"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_access")
    role = models.CharField(max_length=5, choices=Role.choices, default=Role.BASIC)


class RequestWindow(models.Model):
    # HMAC: no almacenamos IP ni nombre de usuario en claro en los contadores.
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
