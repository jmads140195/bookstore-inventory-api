from django.urls import path
from .views import CurrentRateView, RefreshRateView

urlpatterns = [path("rates/current", CurrentRateView.as_view()), path("rates/refresh", RefreshRateView.as_view())]
