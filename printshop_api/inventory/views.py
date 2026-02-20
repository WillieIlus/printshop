# inventory/views.py

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from shops.models import Shop
from shops.permissions import IsShopOwner, IsShopManagerOrOwner, IsShopMember

from .models import Machine, MachineCapability, Material, MaterialStock, PaperStock
from .serializers import (
    MachineSerializer, 
    MachineWithCapabilitiesCreateSerializer,
    MachineCapabilitySerializer,
    MaterialSerializer,
    MaterialStockSerializer,
    PaperStockSerializer,
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
        """Only shop owner can manage machines (onboarding)."""
        return [permissions.IsAuthenticated(), IsShopOwner()]

    def _check_machine_limit(self, shop, machine_type):
        """Enforce subscription limits. Returns (allowed, error_message)."""
        from subscription.models import Subscription, SubscriptionPlan
        from subscription.views import get_subscription_for_shop

        try:
            sub = get_subscription_for_shop(shop)
        except Exception:
            sub = None
        if not sub:
            plan = SubscriptionPlan.objects.filter(is_active=True).order_by("price").first()
            if plan:
                max_printing = plan.max_printing_machines
                max_finishing = plan.max_finishing_machines
            else:
                max_printing, max_finishing = 1, 0
            printing_count = Machine.objects.filter(
                shop=shop,
                machine_type__in=[
                    Machine.MachineType.DIGITAL,
                    Machine.MachineType.LARGE_FORMAT,
                    Machine.MachineType.OFFSET,
                ],
            ).count()
            finishing_count = Machine.objects.filter(
                shop=shop, machine_type=Machine.MachineType.FINISHING
            ).count()
            if machine_type == Machine.MachineType.FINISHING:
                if max_finishing > 0 and finishing_count >= max_finishing:
                    return False, f"Upgrade required: your plan allows {max_finishing} finishing machine(s)."
            else:
                if max_printing > 0 and printing_count >= max_printing:
                    return False, f"Upgrade required: your plan allows {max_printing} printing machine(s)."
            return True, None

        if sub.status not in [Subscription.Status.ACTIVE, Subscription.Status.TRIAL]:
            return False, "Upgrade required: your subscription is not active."
        if sub.current_period_end and sub.current_period_end < timezone.now():
            return False, "Upgrade required: your subscription has expired."

        plan = sub.plan
        printing_count = Machine.objects.filter(
            shop=shop,
            machine_type__in=[
                Machine.MachineType.DIGITAL,
                Machine.MachineType.LARGE_FORMAT,
                Machine.MachineType.OFFSET,
            ],
        ).count()
        finishing_count = Machine.objects.filter(
            shop=shop, machine_type=Machine.MachineType.FINISHING
        ).count()

        if machine_type == Machine.MachineType.FINISHING:
            if plan.max_finishing_machines > 0 and finishing_count >= plan.max_finishing_machines:
                return False, f"Upgrade required: your plan allows {plan.max_finishing_machines} finishing machine(s)."
        else:
            if plan.max_printing_machines > 0 and printing_count >= plan.max_printing_machines:
                return False, f"Upgrade required: your plan allows {plan.max_printing_machines} printing machine(s)."
        return True, None

    def perform_create(self, serializer):
        shop = self.get_shop()
        machine_type = serializer.validated_data.get("machine_type", Machine.MachineType.DIGITAL)
        allowed, msg = self._check_machine_limit(shop, machine_type)
        if not allowed:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(msg)
        serializer.save(shop=shop)


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


# =============================================================================
# Paper Stock ViewSet (works with actual PaperStock model)
# =============================================================================

class PaperStockViewSet(viewsets.ModelViewSet):
    """
    Manage paper stock (inventory) for a shop.
    Endpoint: /api/shops/{shop_slug}/paper-stock/
    """
    serializer_class = PaperStockSerializer

    def get_shop(self):
        if not hasattr(self, "_shop"):
            self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return self._shop

    def get_queryset(self):
        return PaperStock.objects.filter(shop=self.get_shop()).order_by("sheet_size", "gsm")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = self.get_shop()
        return context

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), IsShopMember()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]

    @action(detail=True, methods=['post'])
    def adjust(self, request, shop_slug=None, pk=None):
        """
        Adjust stock quantity.
        Body: {"adjustment": 10} or {"adjustment": -5}
        """
        stock = self.get_object()
        try:
            adjustment = int(request.data.get("adjustment", 0))
        except (ValueError, TypeError):
            return Response({"error": "Invalid adjustment value"}, status=status.HTTP_400_BAD_REQUEST)

        stock.quantity_in_stock += adjustment
        if stock.quantity_in_stock < 0:
            stock.quantity_in_stock = 0

        stock.save()
        return Response(PaperStockSerializer(stock).data)