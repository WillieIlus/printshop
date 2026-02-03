# inventory/views.py

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from shops.models import Shop
from shops.permissions import IsShopManagerOrOwner, IsShopMember

from .models import Machine, MachineCapability, Material, MaterialStock
from .serializers import (
    MachineSerializer, 
    MachineWithCapabilitiesCreateSerializer,
    MachineCapabilitySerializer,
    MaterialSerializer,
    MaterialStockSerializer
)

# =============================================================================
# Machine ViewSets
# =============================================================================

class MachineViewSet(viewsets.ModelViewSet):
    """
    Manage Machines for a specific shop.
    Endpoint: /api/shops/{shop_slug}/machines/
    """
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MachineWithCapabilitiesCreateSerializer
        return MachineSerializer

    def get_shop(self):
        """Get shop from URL slug and cache it."""
        if not hasattr(self, "_shop"):
            self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return self._shop

    def get_queryset(self):
        """Filter machines by shop."""
        return Machine.objects.filter(shop=self.get_shop()).order_by("name")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = self.get_shop()
        return context

    def get_permissions(self):
        """
        Members can view machines.
        Only Managers/Owners can manage (create/update/delete) them.
        """
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), IsShopMember()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]


class MachineCapabilityViewSet(viewsets.ModelViewSet):
    """
    Manage capabilities for a specific machine.
    Endpoint: /api/shops/{shop_slug}/machines/{machine_pk}/capabilities/
    """
    serializer_class = MachineCapabilitySerializer

    def get_machine(self):
        shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return get_object_or_404(Machine, pk=self.kwargs["machine_pk"], shop=shop)

    def get_queryset(self):
        return MachineCapability.objects.filter(machine=self.get_machine())

    def perform_create(self, serializer):
        serializer.save(machine=self.get_machine())

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), IsShopMember()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]


# =============================================================================
# Material ViewSets
# =============================================================================

class MaterialViewSet(viewsets.ModelViewSet):
    """
    Manage Materials for a specific shop.
    Endpoint: /api/shops/{shop_slug}/materials/
    """
    serializer_class = MaterialSerializer

    def get_shop(self):
        if not hasattr(self, "_shop"):
            self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return self._shop

    def get_queryset(self):
        return Material.objects.filter(shop=self.get_shop()).order_by("name")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = self.get_shop()
        return context

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), IsShopMember()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]


class MaterialStockViewSet(viewsets.ModelViewSet):
    """
    Manage specific stock variants for a material.
    Endpoint: /api/shops/{shop_slug}/materials/{material_pk}/stock/
    """
    serializer_class = MaterialStockSerializer

    def get_material(self):
        shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return get_object_or_404(Material, pk=self.kwargs["material_pk"], shop=shop)

    def get_queryset(self):
        return MaterialStock.objects.filter(material=self.get_material()).order_by("label")

    def perform_create(self, serializer):
        serializer.save(material=self.get_material())

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), IsShopMember()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, shop_slug=None, material_pk=None, pk=None):
        """
        Simple endpoint to increment/decrement stock.
        Body: {"adjustment": 10} or {"adjustment": -5}
        """
        stock = self.get_object()
        try:
            adjustment = int(request.data.get("adjustment", 0))
        except (ValueError, TypeError):
            return Response({"error": "Invalid adjustment value"}, status=status.HTTP_400_BAD_REQUEST)
        
        stock.current_stock_level += adjustment
        if stock.current_stock_level < 0:
            stock.current_stock_level = 0
            
        stock.save()
        return Response(self.get_serializer(stock).data)