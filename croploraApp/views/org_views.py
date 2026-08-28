from rest_framework import viewsets
from croploraApp.models import Organization
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer


class OrgViewset(viewsets.ModelViewSet):
    queryset=Organization.objects.all()
    permission_classes=[IsAuthenticated]
    
    
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
    
    