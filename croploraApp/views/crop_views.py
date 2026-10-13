from typing import Dict, Type

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser,MultiPartParser,FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from croploraApp.models.agriculture import Crop
from croploraApp.serializers.crop_serializers import (
    CropCreateUpdateSerializer,
    CropListSerializer,
)


class CropViewSet(viewsets.ModelViewSet):
    serializer_class = CropCreateUpdateSerializer
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser,MultiPartParser,FormParser]
    action_serializer_map: Dict[str, Type] = {
        "list": CropListSerializer,
        "create": CropCreateUpdateSerializer,
        "update": CropCreateUpdateSerializer,
    }
    http_method_names = ["get", "post", "put", "delete", "head", "options"]

    def get_serializer_class(self):
        return self.action_serializer_map.get(self.action, self.serializer_class)

    def get_queryset(self):
        organization_id = self.request.user.organization_id
        queryset = Crop.objects.filter(
            organization_id=organization_id,
            is_active=True,
            is_deleted=False,
        ).order_by("name", "variety", "id")

        if self.action == "list":
            queryset = queryset.only(
                "id",
                "crop_code",
                "name",
                "crop_type",
                "variety",
            )

        return queryset

    def create(self, request, *args, **kwargs):
        organization_id = self.request.user.organization_id
        if organization_id is None:
            raise ValidationError(
                {"organization": "Your user must belong to an organization."}
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization_id=organization_id)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

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
        self.get_queryset().filter(pk=instance.pk).update(
            is_active=False,
            is_deleted=True,
            updated_at=timezone.now(),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)