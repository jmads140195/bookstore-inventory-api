from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from books.frontend import inventory_app

from .status import home, ready
from .views import health

urlpatterns = [
    path("", home, name="home"),
    path("app", inventory_app, name="inventory-app"),
    path("health", health, name="health"),
    path("ready", ready, name="ready"),
    path("admin/", admin.site.urls),
    path("schema", SpectacularAPIView.as_view(), name="schema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("", include("books.urls")),
    path("", include("accounts.urls")),
    path("", include("rates.urls")),
]
handler404 = "config.exceptions.not_found"
handler500 = "config.exceptions.server_error"
