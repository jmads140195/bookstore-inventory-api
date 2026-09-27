from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ChangePasswordView, LoginView, LogoutAllView, LogoutView, MeView, UserViewSet

router = SimpleRouter(trailing_slash=False)
router.register("users", UserViewSet, basename="user")
urlpatterns = [
    path("auth/login", LoginView.as_view(), name="login"),
    path("auth/me", MeView.as_view(), name="me"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
    path("auth/logout-all", LogoutAllView.as_view(), name="logout-all"),
    path("auth/change-password", ChangePasswordView.as_view(), name="change-password"),
] + router.urls
