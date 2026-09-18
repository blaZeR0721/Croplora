from rest_framework import status, viewsets
from croploraApp.models import Organization
from croploraApp.serializers.org_serializers import OrgCreateUpdateSerializer 
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from typing import Dict, Type

class OrgViewset(viewsets.ModelViewSet):
    queryset = Organization.objects.filter(is_deleted=False)
    renderer_classes=[JSONRenderer]
    parser_classes=[JSONParser,MultiPartParser,FormParser]
    permission_classes = [IsAuthenticated]

    action_serializer_map: Dict[str, Type] = {
        "create": OrgCreateUpdateSerializer,
        "update":OrgCreateUpdateSerializer
    }

    def get_serializer_class(self):
        return self.action_serializer_map.get(self.action,self.serializer_class)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save(update_fields=("is_deleted", "updated_at"))
        return Response(status=status.HTTP_204_NO_CONTENT)


    

