import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections, DatabaseError
from django.utils import timezone
from knox.models import AuthToken

from accounts.models import RequestWindow
from config.exceptions import ExchangeRateUnavailable
from rates.services import refresh_exchange_rate


class Command(BaseCommand):
    help = "Worker: sincroniza al iniciar y a las 08:00/15:00 Caracas; reintentos 1/5/15/60 min."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        while True:
            close_old_connections()
            try:
                status = refresh_exchange_rate()
                if status != "not_due":
                    self.stdout.write(status)
                RequestWindow.objects.filter(expires_at__lt=timezone.now()).delete()
                AuthToken.objects.filter(expiry__lt=timezone.now()).delete()
            except (ExchangeRateUnavailable, DatabaseError):
                self.stderr.write("Sincronización pendiente; se reintentará automáticamente.")
            if options["once"]:
                return
            time.sleep(60)
