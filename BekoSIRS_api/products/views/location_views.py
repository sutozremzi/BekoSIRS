"""
Location API endpoints for KKTC Districts and Areas.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from products.models import District, Area
from products.serializers import DistrictSerializer, AreaSerializer


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for KKTC Districts (İlçe).
    Read-only: list and retrieve only.
    """
    queryset = District.objects.all().order_by('name')
    serializer_class = DistrictSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class AreaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for KKTC Areas (Mahalle/Köy).
    Read-only: list and retrieve only.
    Filterable by district_id query parameter.
    """
    serializer_class = AreaSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def get_queryset(self):
        queryset = Area.objects.all().select_related('district').order_by('district__name', 'name')
        district_id = self.request.query_params.get('district_id', None)
        
        if district_id is not None:
            queryset = queryset.filter(district_id=district_id)
        
        return queryset
