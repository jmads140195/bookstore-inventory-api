import os
import subprocess
import sys
from unittest.mock import patch

from django.db import OperationalError
from django.conf import settings
from django.test import SimpleTestCase, TestCase


class StatusTests(TestCase):
    def test_health_and_ready(self):
        self.assertEqual(self.client.get("/health").json()["status"], "ok")
        self.assertEqual(self.client.get("/ready").json()["database"], "ok")

    @patch("config.status.connection.cursor", side_effect=OperationalError("internal database details"))
    def test_readiness_reports_database_outage_without_details(self, cursor):
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("internal database details", response.content.decode())


class ProductionSettingsTests(SimpleTestCase):
    def load_settings(self, **changes):
        environment = os.environ.copy()
        environment.update({
            "DJANGO_ENV": "production", "DJANGO_DEBUG": "false",
            "DJANGO_SECRET_KEY": "test-only-configuration-key-" + "x" * 60,
            "DJANGO_ALLOWED_HOSTS": "test.example.com",
            "DATABASE_URL": "postgresql://test:test@db:5432/test",
            "LOCAL_CURRENCY": "EUR",
        })
        environment.update(changes)
        return subprocess.run([sys.executable, "-c", "import config.settings"],
                              cwd=settings.BASE_DIR, env=environment, capture_output=True, text=True, timeout=15)

    def test_valid_production_settings_load(self):
        result = self.load_settings()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_production_settings_are_rejected(self):
        cases = [{"DJANGO_DEBUG": "true"}, {"DJANGO_SECRET_KEY": "weak"},
                 {"DATABASE_URL": ""}, {"DATABASE_URL": "sqlite:///test.sqlite3"},
                 {"DJANGO_ALLOWED_HOSTS": "*"}]
        for values in cases:
            with self.subTest(values=values):
                self.assertNotEqual(self.load_settings(**values).returncode, 0)
