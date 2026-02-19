# pricing/views.py
"""
API views for simplified pricing.

Two main use cases:
1. Shop owners: Manage their prices (CRUD)
2. Customers: View rate card and calculate prices
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from shops.models import Shop
from shops.permissions import IsShopOwner, IsShopMember

from .models import (
    PrintingPrice,
    PaperPrice,
    MaterialPrice,
    FinishingService,
    VolumeDiscount,
    PriceCalculator,
    DefaultPrintingPriceTemplate,
    DefaultPaperPriceTemplate,
    DefaultMaterialPriceTemplate,
    DefaultFinishingServiceTemplate,
)
from .serializers import (
    PrintingPriceSerializer,
    PaperPriceSerializer,
    MaterialPriceSerializer,
    FinishingServiceSerializer,
    VolumeDiscountSerializer,
    DefaultPrintingPriceTemplateSerializer,
    DefaultPaperPriceTemplateSerializer,
    DefaultMaterialPriceTemplateSerializer,
    DefaultFinishingServiceTemplateSerializer,
    RateCardSerializer,
    PriceCalculatorInputSerializer,
    PriceCalculatorOutputSerializer,
)
from .services.seeding import seed_shop_pricing


# =============================================================================
# SHOP OWNER VIEWS - Manage Prices
# =============================================================================

class ShopPricingMixin:
    """Base mixin for shop-scoped pricing views."""
    
    def get_shop(self):
        shop_slug = self.kwargs.get("shop_slug")
        return Shop.objects.get(slug=shop_slug)
    
    def get_queryset(self):
        return self.queryset.filter(shop=self.get_shop())
    
    def perform_create(self, serializer):
        serializer.save(shop=self.get_shop())
    
    def perform_update(self, serializer):
        instance = serializer.instance
        if instance and hasattr(instance, "needs_review"):
            serializer.save(needs_review=False)
        else:
            serializer.save()


class PrintingPriceViewSet(ShopPricingMixin, viewsets.ModelViewSet):
    """
    Manage printing prices for a shop.
    
    GET /api/shops/{slug}/pricing/printing/ - List printing prices
    POST /api/shops/{slug}/pricing/printing/ - Create printing price
    PUT /api/shops/{slug}/pricing/printing/{id}/ - Update
    DELETE /api/shops/{slug}/pricing/printing/{id}/ - Delete
    """
    
    queryset = PrintingPrice.objects.all()
    serializer_class = PrintingPriceSerializer
    permission_classes = [IsAuthenticated, IsShopMember]


class PaperPriceViewSet(ShopPricingMixin, viewsets.ModelViewSet):
    """
    Manage paper prices (GSM rate card) for a shop.
    
    GET /api/shops/{slug}/pricing/paper/ - List paper prices
    POST /api/shops/{slug}/pricing/paper/ - Create paper price
    """
    
    queryset = PaperPrice.objects.all()
    serializer_class = PaperPriceSerializer
    permission_classes = [IsAuthenticated, IsShopMember]


class FinishingServiceViewSet(ShopPricingMixin, viewsets.ModelViewSet):
    """
    Manage finishing services for a shop.
    
    GET /api/shops/{slug}/pricing/finishing/ - List finishing services
    POST /api/shops/{slug}/pricing/finishing/ - Create finishing service
    """
    
    queryset = FinishingService.objects.all()
    serializer_class = FinishingServiceSerializer
    permission_classes = [IsAuthenticated, IsShopMember]


class VolumeDiscountViewSet(ShopPricingMixin, viewsets.ModelViewSet):
    """
    Manage volume discounts for a shop.
    """
    
    queryset = VolumeDiscount.objects.all()
    serializer_class = VolumeDiscountSerializer
    permission_classes = [IsAuthenticated, IsShopOwner]


class MaterialPriceViewSet(ShopPricingMixin, viewsets.ModelViewSet):
    """
    Manage material prices (SQM) for a shop.
    """
    
    queryset = MaterialPrice.objects.all()
    serializer_class = MaterialPriceSerializer
    permission_classes = [IsAuthenticated, IsShopMember]


# =============================================================================
# DEFAULT TEMPLATES - Public read-only
# =============================================================================

class DefaultPrintingPriceTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DefaultPrintingPriceTemplate.objects.all()
    serializer_class = DefaultPrintingPriceTemplateSerializer
    permission_classes = [AllowAny]


class DefaultPaperPriceTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DefaultPaperPriceTemplate.objects.all()
    serializer_class = DefaultPaperPriceTemplateSerializer
    permission_classes = [AllowAny]


class DefaultMaterialPriceTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DefaultMaterialPriceTemplate.objects.all()
    serializer_class = DefaultMaterialPriceTemplateSerializer
    permission_classes = [AllowAny]


class DefaultFinishingServiceTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DefaultFinishingServiceTemplate.objects.all()
    serializer_class = DefaultFinishingServiceTemplateSerializer
    permission_classes = [AllowAny]


# =============================================================================
# SHOP PRICING ACTIONS - Seed defaults, status
# =============================================================================

class SeedDefaultsView(APIView):
    """
    POST /api/shops/<slug>/pricing/seed-defaults/
    Body: { machine_ids?: number[], overwrite?: boolean }
    Permission: shop owner/admin only
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def post(self, request, shop_slug):
        try:
            shop = Shop.objects.get(slug=shop_slug)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        if shop.owner != request.user and not request.user.is_staff:
            return Response({"error": "Only shop owner or admin can seed defaults"}, status=status.HTTP_403_FORBIDDEN)

        machine_ids = request.data.get("machine_ids")
        overwrite = request.data.get("overwrite", False)

        result = seed_shop_pricing(shop, machine_ids=machine_ids, overwrite=overwrite)
        return Response(result, status=status.HTTP_200_OK)


class PricingStatusView(APIView):
    """
    GET /api/shops/<slug>/pricing/status/
    Returns counts of rows and needs_review per category.
    """
    permission_classes = [IsAuthenticated, IsShopMember]

    def get(self, request, shop_slug):
        try:
            shop = Shop.objects.get(slug=shop_slug)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        printing = PrintingPrice.objects.filter(shop=shop)
        paper = PaperPrice.objects.filter(shop=shop)
        material = MaterialPrice.objects.filter(shop=shop)
        finishing = FinishingService.objects.filter(shop=shop)

        data = {
            "printing": {"total": printing.count(), "needs_review": printing.filter(needs_review=True).count()},
            "paper": {"total": paper.count(), "needs_review": paper.filter(needs_review=True).count()},
            "material": {"total": material.count(), "needs_review": material.filter(needs_review=True).count()},
            "finishing": {"total": finishing.count(), "needs_review": finishing.filter(needs_review=True).count()},
        }
        return Response(data)


# =============================================================================
# PUBLIC VIEWS - For Customers
# =============================================================================

class RateCardView(APIView):
    """
    Public rate card for a shop.
    
    GET /api/shops/{slug}/rate-card/
    
    Returns:
    - Printing prices per side
    - Paper prices by GSM  
    - Finishing services
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, shop_slug):
        try:
            shop = Shop.objects.get(slug=shop_slug, is_active=True)
        except Shop.DoesNotExist:
            return Response(
                {"error": "Shop not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get printing prices
        printing = PrintingPrice.objects.filter(shop=shop, is_active=True)
        printing_data = [
            {
                "sheet_size": p.sheet_size,
                "color_mode": p.get_color_mode_display(),
                "price_per_side": p.selling_price_per_side,
                "price_double_sided": p.get_price_for_sides(2)
            }
            for p in printing
        ]
        
        # Get paper prices  
        paper = PaperPrice.objects.filter(shop=shop, is_active=True)
        paper_data = [
            {
                "gsm": p.gsm,
                "paper_type": p.get_paper_type_display(),
                "price_per_sheet": p.selling_price
            }
            for p in paper
        ]
        
        # Get finishing services
        finishing = FinishingService.objects.filter(shop=shop, is_active=True)
        finishing_data = [
            {
                "id": f.id,
                "name": f.name,
                "category": f.get_category_display(),
                "price": f.selling_price,
                "charge_by": f.get_charge_by_display(),
                "is_default": f.is_default
            }
            for f in finishing
        ]
        
        data = {
            "printing": printing_data,
            "paper": paper_data,
            "finishing": finishing_data
        }
        
        serializer = RateCardSerializer(data)
        return Response(serializer.data)


class CalculatePriceView(APIView):
    """
    Calculate price for a print job.
    
    POST /api/shops/{slug}/calculate-price/
    
    Body:
    {
        "sheet_size": "A3",
        "gsm": 300,
        "quantity": 100,
        "sides": 2,
        "paper_type": "GLOSS",
        "finishing_ids": [1, 2]
    }
    
    Returns breakdown:
    - Printing cost
    - Paper cost
    - Finishing cost
    - Grand total
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request, shop_slug):
        try:
            shop = Shop.objects.get(slug=shop_slug, is_active=True)
        except Shop.DoesNotExist:
            return Response(
                {"error": "Shop not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate input
        input_serializer = PriceCalculatorInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(
                input_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate price
        data = input_serializer.validated_data
        calc_kwargs = {
            "shop": shop,
            "quantity": data["quantity"],
            "sides": data.get("sides", 1),
            "paper_type": data.get("paper_type", "GLOSS"),
            "finishing_ids": data.get("finishing_ids", []),
        }
        if data.get("unit") == "SQM":
            calc_kwargs["material_type"] = data.get("material_type")
            calc_kwargs["unit"] = "SQM"
            calc_kwargs["area_sqm"] = data.get("area_sqm")
        else:
            calc_kwargs["sheet_size"] = data.get("sheet_size")
            calc_kwargs["gsm"] = data.get("gsm")
        result = PriceCalculator.calculate(**calc_kwargs)
        
        # Return result
        output_serializer = PriceCalculatorOutputSerializer(result)
        return Response(output_serializer.data)


# =============================================================================
# LEGACY COMPATIBILITY - Keep old API endpoints working
# =============================================================================

# Aliases for backward compatibility
SimpleRateCardView = RateCardView
SimplePriceCalculatorView = CalculatePriceView
