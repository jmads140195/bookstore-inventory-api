from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone
from knox.models import AuthToken
from rest_framework.test import APITestCase

from books.models import Book
from books.test_api import book_data
from .models import RequestWindow, UserAccess

User = get_user_model()
PASSWORD = "Tests-only!4vN7pX2rQ9"
NEW_PASSWORD = "Tests-only!6bM8cZ1wL3"


class AccessTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.full = User.objects.create_user("manager", password=PASSWORD)
        UserAccess.objects.create(user=cls.full, role="full")
        cls.basic = User.objects.create_user("reader", password=PASSWORD)
        UserAccess.objects.create(user=cls.basic, role="basic")
        cls.book = Book.objects.create(**book_data(isbn="9788437604947"))

    def token_for(self, user):
        instance, token = AuthToken.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return instance, token

    def login(self, username="manager", password=PASSWORD):
        self.client.credentials()
        return self.client.post("/auth/login", {"username": username, "password": password}, format="json")

    def test_login_returns_expiring_token_and_hash_is_stored(self):
        response = self.login()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response.data["token_type"], "Bearer")
        self.assertEqual(response.data["user"]["role"], "full")
        self.assertNotIn("password", response.data["user"])
        instance = AuthToken.objects.get(user=self.full)
        self.assertNotEqual(instance.digest, response.data["token"])
        self.assertGreater(instance.expiry, timezone.now() + timedelta(hours=7))
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["token"])
        self.assertEqual(self.client.get("/auth/me").status_code, 200)

    def test_invalid_unknown_and_disabled_login_have_identical_error(self):
        self.basic.is_active = False
        self.basic.save()
        responses = [self.login(password="wrong"), self.login(username="missing"), self.login(username="reader")]
        self.assertTrue(all(r.status_code == 401 for r in responses))
        self.assertEqual(responses[0].data, responses[1].data)
        self.assertEqual(responses[1].data, responses[2].data)

    def test_anonymous_cannot_read_or_modify_inventory(self):
        self.assertEqual(self.client.get("/books").status_code, 401)
        self.assertEqual(self.client.post("/books", book_data(), format="json").status_code, 401)
        self.assertEqual(self.client.get("/users").status_code, 401)
        for path in ["/health", "/ready", "/docs", "/schema"]:
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_basic_can_read_but_cannot_modify_books_or_users(self):
        self.token_for(self.basic)
        for path in ["/books", f"/books/{self.book.pk}", "/books/search?category=Novela", "/books/low-stock", "/rates/current", "/auth/me"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response["Cache-Control"], "no-store")
        for method, path in [("post", "/books"), ("put", f"/books/{self.book.pk}"),
                             ("patch", f"/books/{self.book.pk}"), ("delete", f"/books/{self.book.pk}"),
                             ("post", f"/books/{self.book.pk}/calculate-price"), ("post", "/users"),
                             ("get", "/users"), ("patch", f"/users/{self.basic.pk}"), ("post", "/rates/refresh")]:
            self.assertEqual(getattr(self.client, method)(path).status_code, 403, path)
        self.book.refresh_from_db()
        self.assertIsNone(self.book.selling_price_local)

    def test_full_creates_basic_by_default_and_full_when_explicit(self):
        self.token_for(self.full)
        for username, role in [("newreader", None), ("newmanager", "full")]:
            payload = {"username": username, "password": NEW_PASSWORD}
            if role:
                payload["role"] = role
            response = self.client.post("/users", payload, format="json")
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data["role"], role or "basic")
            user = User.objects.get(username=username)
            self.assertTrue(user.check_password(NEW_PASSWORD))
            self.assertFalse(user.is_staff)
            self.assertFalse(user.is_superuser)

    def test_creation_rejects_weak_password_duplicates_and_privilege_injection(self):
        self.token_for(self.full)
        for extra in [{"password": "123"}, {"is_superuser": True}, {"is_staff": True},
                      {"role": "root"}, {"username": "manager"}, {"username": "MANAGER"}]:
            payload = {"username": "new", "password": NEW_PASSWORD, **extra}
            self.assertEqual(self.client.post("/users", payload, format="json").status_code, 400)
        self.assertEqual(User.objects.count(), 2)

    def test_role_change_and_deactivation_revoke_sessions(self):
        basic_instance, _ = AuthToken.objects.create(user=self.basic)
        self.token_for(self.full)
        response = self.client.patch(f"/users/{self.basic.pk}", {"role": "full"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuthToken.objects.filter(pk=basic_instance.pk).exists())
        self.assertEqual(response.data["role"], "full")
        _, token = AuthToken.objects.create(user=self.basic)
        self.assertEqual(self.client.patch(f"/users/{self.basic.pk}", {"is_active": False}, format="json").status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/books").status_code, 401)

    def test_cannot_demote_self_or_modify_django_superuser(self):
        self.token_for(self.full)
        self.assertEqual(self.client.patch(f"/users/{self.full.pk}", {"role": "basic"}, format="json").status_code, 400)
        root = User.objects.create_superuser("root", password=PASSWORD)
        self.assertEqual(self.client.patch(f"/users/{root.pk}", {"is_active": False}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/users/{self.basic.pk}").status_code, 405)

    def test_expired_and_invalid_tokens_are_rejected(self):
        instance, _ = self.token_for(self.basic)
        AuthToken.objects.filter(pk=instance.pk).update(expiry=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get("/books").status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid")
        self.assertEqual(self.client.get("/books").status_code, 401)

    def test_logout_revokes_only_current_token(self):
        other, _ = AuthToken.objects.create(user=self.full)
        self.token_for(self.full)
        self.assertEqual(self.client.post("/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)
        self.assertTrue(AuthToken.objects.filter(pk=other.pk).exists())

    def test_logout_all_revokes_all_tokens(self):
        AuthToken.objects.create(user=self.full)
        self.token_for(self.full)
        self.assertEqual(self.client.post("/auth/logout-all").status_code, 204)
        self.assertEqual(AuthToken.objects.filter(user=self.full).count(), 0)

    def test_password_change_requires_current_password_and_revokes_tokens(self):
        self.token_for(self.basic)
        payload = {"current_password": "wrong", "new_password": NEW_PASSWORD}
        self.assertEqual(self.client.post("/auth/change-password", payload, format="json").status_code, 400)
        payload["current_password"] = PASSWORD
        self.assertEqual(self.client.post("/auth/change-password", payload, format="json").status_code, 204)
        self.assertFalse(AuthToken.objects.filter(user=self.basic).exists())
        self.basic.refresh_from_db()
        self.assertTrue(self.basic.check_password(NEW_PASSWORD))

    def test_full_can_reset_another_users_password(self):
        AuthToken.objects.create(user=self.basic)
        self.token_for(self.full)
        self.assertEqual(self.client.post(f"/users/{self.basic.pk}/reset-password", {"new_password": NEW_PASSWORD}, format="json").status_code, 204)
        self.basic.refresh_from_db()
        self.assertTrue(self.basic.check_password(NEW_PASSWORD))
        self.assertFalse(AuthToken.objects.filter(user=self.basic).exists())

    @override_settings(LOGIN_USER_LIMIT=2)
    def test_login_limit_is_shared_and_returns_retry_after(self):
        self.assertEqual(self.login(password="bad").status_code, 401)
        self.assertEqual(self.login(password="bad").status_code, 401)
        response = self.login(password="bad")
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        self.assertNotIn("manager", str(list(RequestWindow.objects.values())))

    @override_settings(API_USER_LIMIT=1)
    def test_authenticated_rate_limit(self):
        self.token_for(self.basic)
        self.assertEqual(self.client.get("/books").status_code, 200)
        self.assertEqual(self.client.get("/books").status_code, 429)

    @override_settings(AUTH_MAX_TOKENS=1)
    def test_session_limit(self):
        self.token_for(self.full)
        self.assertEqual(self.login().status_code, 429)

    def test_large_json_body_is_rejected(self):
        self.token_for(self.full)
        self.assertEqual(self.client.post("/books", {"title": "x" * 70000}, format="json").status_code, 413)
        self.assertEqual(self.client.post("/auth/login", {"username": "x" * 70000}, format="json").status_code, 413)


class BootstrapTests(APITestCase):
    def test_initial_admin_is_created_once_without_reset_or_staff_access(self):
        with patch.dict("os.environ", {"BOOTSTRAP_ADMIN_USERNAME": "first", "BOOTSTRAP_ADMIN_PASSWORD": PASSWORD}):
            call_command("bootstrap_api_admin", stdout=StringIO())
            call_command("bootstrap_api_admin", stdout=StringIO())
        user = User.objects.get(username="first")
        self.assertEqual(user.api_access.role, "full")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.is_staff)
        with patch.dict("os.environ", {"BOOTSTRAP_ADMIN_USERNAME": "second", "BOOTSTRAP_ADMIN_PASSWORD": PASSWORD}):
            with self.assertRaises(CommandError):
                call_command("bootstrap_api_admin", stdout=StringIO())
