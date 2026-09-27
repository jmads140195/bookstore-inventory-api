import hashlib
import hmac
from collections.abc import Mapping
from datetime import datetime, timezone as datetime_timezone

from django.conf import settings
from django.db.models import F
from django.utils import timezone
from rest_framework.throttling import BaseThrottle

from .models import RequestWindow


def consume(scope, identity, limit, seconds):
    now = timezone.now().timestamp()
    bucket = int(now // seconds)
    end = (bucket + 1) * seconds
    raw = f"{scope}:{identity}:{bucket}".encode()
    key = hmac.new(settings.SECRET_KEY.encode(), raw, hashlib.sha256).hexdigest()
    row, _ = RequestWindow.objects.get_or_create(
        key=key, defaults={"expires_at": datetime.fromtimestamp(end, datetime_timezone.utc)})
    allowed = RequestWindow.objects.filter(pk=row.pk, count__lt=limit).update(count=F("count") + 1)
    return bool(allowed), max(1, int(end - now) + 1)


class DatabaseThrottle(BaseThrottle):
    remaining = None

    def client_ip(self, request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        count = settings.AUTH_TRUSTED_PROXY_COUNT
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if count and len(parts) >= count:
            return parts[-count]
        return request.META.get("REMOTE_ADDR", "unknown")

    def check(self, scope, identity, limit, seconds):
        allowed, self.remaining = consume(scope, identity, limit, seconds)
        return allowed

    def wait(self):
        return self.remaining


class LoginThrottle(DatabaseThrottle):
    def allow_request(self, request, view):
        if not self.check("login-ip", self.client_ip(request), settings.LOGIN_IP_LIMIT, 900):
            return False
        data = request.data
        username = data.get("username", "") if isinstance(data, Mapping) else ""
        return self.check("login-user", str(username).strip().casefold()[:150], settings.LOGIN_USER_LIMIT, 900)


class UserThrottle(DatabaseThrottle):
    def allow_request(self, request, view):
        identity = f"user:{request.user.pk}" if request.user.is_authenticated else f"ip:{self.client_ip(request)}"
        return self.check("api", identity, settings.API_USER_LIMIT, 60)


class RefreshRateThrottle(DatabaseThrottle):
    def allow_request(self, request, view):
        return self.check("rate-refresh", "global", 1, 60)
