from rest_framework import status, viewsets
from croploraApp.models.organization import Organization
from croploraApp.serializers.org_serializers import OrgCreateUpdateSerializer 
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import CursorPagination
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from typing import Dict, Type
from django.db.models import Prefetch
from croploraApp.models.reference import Address
from croploraApp.views.utils.choicefields import AddressSourceChoice


class OrganizationCursorPagination(CursorPagination):
    page_size = 20
    ordering = "-id"


class OrgViewset(viewsets.ModelViewSet):
    queryset = Organization.objects.filter(is_deleted=False)
    serializer_class = OrgCreateUpdateSerializer
    pagination_class = OrganizationCursorPagination
    renderer_classes=[JSONRenderer]
    parser_classes=[JSONParser,MultiPartParser,FormParser]
    permission_classes = [IsAuthenticated]

    action_serializer_map: Dict[str, Type] = {
        "create": OrgCreateUpdateSerializer,
        "update":OrgCreateUpdateSerializer
    }

    def get_serializer_class(self):
        return self.action_serializer_map.get(self.action,self.serializer_class)

    def get_queryset(self):
        queryset = Organization.objects.filter(is_deleted=False)
        if self.action == "list":
            company_addresses = Address.objects.filter(
                address_source=AddressSourceChoice.COMPANY,
            )
            queryset = queryset.prefetch_related(
                Prefetch(
                    "addresses",
                    queryset=company_addresses,
                    to_attr="company_addresses",
                )
            )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.is_active = False
        instance.save(update_fields=("is_deleted","is_active", "updated_at"))
        return Response(status=status.HTTP_204_NO_CONTENT)


    
