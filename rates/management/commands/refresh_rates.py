from django.core.management.base import BaseCommand, CommandError
from config.exceptions import ExchangeRateUnavailable
from rates.services import refresh_exchange_rate


class Command(BaseCommand):
    help = "Actualiza la tasa persistida si corresponde (o fuerza con --force)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        try:
            self.stdout.write(refresh_exchange_rate(force=options["force"]))
        except ExchangeRateUnavailable as exc:
            raise CommandError(str(exc.detail)) from exc
