from rest_framework.routers import SimpleRouter

from .views import BookViewSet

router = SimpleRouter(trailing_slash=False)
router.register("books", BookViewSet, basename="book")
urlpatterns = router.urls
