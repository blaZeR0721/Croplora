from rest_framework import mixins, viewsets
from croploraApp.serializers.common_serializers import CountrySerializer,StateSerializer  
from croploraApp.models import Country,State
from rest_framework.permissions import IsAuthenticated

class CountryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = CountrySerializer
    queryset = Country.objects.all().order_by("name")
    permission_classes=[IsAuthenticated]

class StateViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = StateSerializer

    def get_queryset(self):
        queryset = State.objects.select_related("country").order_by("name")

        country_id = self.request.query_params.get("country")
        if country_id:
            queryset = queryset.filter(country_id=country_id)

        return queryset