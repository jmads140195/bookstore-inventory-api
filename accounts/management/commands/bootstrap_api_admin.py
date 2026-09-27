"""Crea el primer administrador de la API sin contraseñas en argumentos o logs."""
import getpass
import os

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import UserAccess


class Command(BaseCommand):
    help = "Crear el administrador inicial (interactivo o BOOTSTRAP_ADMIN_USERNAME/PASSWORD)."

    def add_arguments(self, parser):
        parser.add_argument("--username")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"] or os.getenv("BOOTSTRAP_ADMIN_USERNAME")
        if not username:
            raise CommandError("Indica --username o BOOTSTRAP_ADMIN_USERNAME.")
        existing = User.objects.filter(username=username).first()
        if existing:
            if existing.is_active and (existing.is_superuser or UserAccess.objects.filter(user=existing, role="full").exists()):
                self.stdout.write("Administrador existente: se conserva su contraseña y configuración.")
                return
            raise CommandError("El usuario ya existe sin acceso completo activo; no se modifica.")
        if UserAccess.objects.filter(role="full", user__is_active=True).exists() or User.objects.filter(is_superuser=True, is_active=True).exists():
            raise CommandError("Ya existe un administrador. Crea los siguientes desde POST /users.")
        password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or getpass.getpass("Contraseña inicial (mínimo 12 caracteres): ")
        user = User(username=username)
        try:
            user.full_clean(exclude=["password"])
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        with transaction.atomic():
            user.set_password(password)
            user.save()
            UserAccess.objects.create(user=user, role="full")
        self.stdout.write(self.style.SUCCESS("Administrador de API creado. No tiene acceso a /admin/."))
