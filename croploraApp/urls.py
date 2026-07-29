from rest_framework.routers import DefaultRouter
from .views.auth_views import AuthViewSet
from .views.common_views import CountryViewSet,StateViewSet

router = DefaultRouter()

router.register(r"auth", AuthViewSet, basename="auth")
router.register(r"countries", CountryViewSet, basename="country")
router.register(r"states", StateViewSet, basename="state")

urlpatterns = router.urls

