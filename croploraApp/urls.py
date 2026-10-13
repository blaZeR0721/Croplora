from rest_framework.routers import DefaultRouter
from .views.auth_views import AuthViewSet
from .views.common_views import CountryViewSet,StateViewSet
from .views.crop_views import CropViewSet
from .views.org_views import OrgViewset

router = DefaultRouter()

router.register(r"auth", AuthViewSet, basename="auth")
router.register(r"countries", CountryViewSet, basename="country")
router.register(r"states", StateViewSet, basename="state")
router.register(r"crops", CropViewSet, basename="crop")
router.register(r"organization",OrgViewset,basename="organization")

urlpatterns = router.urls

