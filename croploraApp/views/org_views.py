from rest_framework import status, viewsets
from croploraApp.models.organization import Organization
from croploraApp.serializers.org_serializers import OrgCreateUpdateSerializer 
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from typing import Dict, Type
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from croploraApp.models.reference import Address
from croploraApp.models.organization import OrgUser
from croploraApp.views.utils.choicefields import AddressSourceChoice
from croploraApp.views.utils.choicefields import OrgRoleTypeChoice
from croploraApp.serializers.org_serializers import OwnerDetailsSerializer
from rest_framework.decorators import action

class OrgViewset(viewsets.ModelViewSet):
    queryset = Organization.objects.filter(is_deleted=False)
    serializer_class = OrgCreateUpdateSerializer
    renderer_classes=[JSONRenderer]
    parser_classes=[JSONParser,MultiPartParser,FormParser]
    permission_classes = [IsAuthenticated]

    action_serializer_map: Dict[str, Type] = {
        "create": OrgCreateUpdateSerializer,
        "update": OrgCreateUpdateSerializer,
        "owner_details": OwnerDetailsSerializer,
    }

    def get_serializer_class(self):
        return self.action_serializer_map.get(self.action,self.serializer_class)

    def get_queryset(self):
        queryset = Organization.objects.filter(is_deleted=False)
        if self.action in {"list", "retrieve", "update"}:
            company_addresses = Address.objects.filter(
                address_source=AddressSourceChoice.COMPANY,
            )
            if self.action == "update":
                company_addresses = company_addresses.select_related("country")
            if self.action == "list":
                company_addresses = company_addresses.only(
                    "id",
                    "organization_id",
                    "address_line_1",
                    "address_line_2",
                    "country_id",
                    "state_id",
                    "postal_code",
                    "landmark",
                )
                queryset = queryset.only(
                    "id",
                    "name",
                    "org_phone_number",
                    "website_url",
                    "social_media_links",
                    "logo",
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

    @action(detail=False, methods=["PUT"], url_path="owner-details")
    def owner_details(self, request, *args, **kwargs):
        owner = get_object_or_404(
            OrgUser.objects.select_related(
                "address__country",
                "address__state",
                "organization",
                "org_role",
            ),
            user_id=request.user.pk,
            organization_id=request.user.organization_id,
            org_role__role_code=OrgRoleTypeChoice.OWNER,
            is_active=True,
            is_deleted=False,
        )
        serializer = self.get_serializer(owner, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
