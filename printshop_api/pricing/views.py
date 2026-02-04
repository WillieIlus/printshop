# pricing/views.py

from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from shops.models import Shop
from shops.permissions import IsShopManagerOrOwner, IsShopMember
from inventory.models import Machine, Material

from .models import (
    DigitalPrintPrice,
    MaterialPrice,
    FinishingPrice,
    PaperGSMPrice,
    VolumeDiscount,
)
from .serializers import (
    DigitalPrintPriceSerializer,
    DigitalPrintPriceListSerializer,
    MaterialPriceSerializer,
    MaterialPriceListSerializer,
    FinishingPriceSerializer,
    FinishingPriceListSerializer,
    VolumeDiscountSerializer,
    MachinePriceCardSerializer,
    MaterialPriceCardSerializer,
    FullRateCardSerializer,
    PrintCostCalculatorSerializer,
    PrintCostResultSerializer,
    # Simple pricing serializers
    PaperGSMPriceSerializer,
    PaperGSMPriceListSerializer,
    SimplePriceCalculatorInputSerializer,
    SimplePriceCalculatorOutputSerializer,
)


# =============================================================================
# Base Mixin for Shop-scoped ViewSets
# =============================================================================

class ShopScopedMixin:
    """Mixin to handle shop scoping for pricing viewsets."""
    
    def get_shop(self):
        """Get and cache the shop from URL."""
        if not hasattr(self, "_shop"):
            self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return self._shop
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = self.get_shop()
        return context
    
    def get_permissions(self):
        """Members can view, managers can modify."""
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated(), IsShopMember()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]


# =============================================================================
# Digital Print Price ViewSet
# =============================================================================

class DigitalPrintPriceViewSet(ShopScopedMixin, viewsets.ModelViewSet):
    """
    Manage digital printing prices for a shop.
    Endpoint: /api/shops/{shop_slug}/pricing/print/
    """
    
    def get_serializer_class(self):
        if self.action == "list":
            return DigitalPrintPriceListSerializer
        return DigitalPrintPriceSerializer
    
    def get_queryset(self):
        return DigitalPrintPrice.objects.filter(
            shop=self.get_shop()
        ).select_related("machine").order_by("machine__name", "sheet_size")
    
    @action(detail=False, methods=["get"])
    def by_machine(self, request, shop_slug=None):
        """Group prices by machine for easier viewing."""
        shop = self.get_shop()
        machines = Machine.objects.filter(shop=shop, is_active=True)
        
        result = []
        for machine in machines:
            prices = DigitalPrintPrice.objects.filter(
                machine=machine, shop=shop
            ).order_by("sheet_size", "color_mode")
            
            result.append({
                "machine": {
                    "id": machine.id,
                    "name": machine.name,
                    "type": machine.get_type_display(),
                },
                "prices": DigitalPrintPriceListSerializer(prices, many=True).data
            })
        
        return Response(result)


# =============================================================================
# Material Price ViewSet
# =============================================================================

class MaterialPriceViewSet(ShopScopedMixin, viewsets.ModelViewSet):
    """
    Manage material selling prices for a shop.
    Endpoint: /api/shops/{shop_slug}/pricing/materials/
    """
    
    def get_serializer_class(self):
        if self.action == "list":
            return MaterialPriceListSerializer
        return MaterialPriceSerializer
    
    def get_queryset(self):
        return MaterialPrice.objects.filter(
            shop=self.get_shop()
        ).select_related("material").order_by("material__name")
    
    @action(detail=False, methods=["post"])
    def bulk_update_markup(self, request, shop_slug=None):
        """
        Bulk update markup percentage for all materials.
        Body: {"markup_percentage": 50, "material_type": "SHEET"}
        """
        shop = self.get_shop()
        markup = request.data.get("markup_percentage")
        material_type = request.data.get("material_type")
        
        if markup is None:
            return Response(
                {"error": "markup_percentage is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = MaterialPrice.objects.filter(shop=shop)
        if material_type:
            queryset = queryset.filter(material__type=material_type)
        
        updated = queryset.update(
            pricing_method=MaterialPrice.PricingMethod.MARKUP,
            markup_percentage=Decimal(str(markup))
        )
        
        return Response({
            "message": f"Updated {updated} material prices",
            "markup_percentage": markup
        })


# =============================================================================
# Finishing Price ViewSet
# =============================================================================

class FinishingPriceViewSet(ShopScopedMixin, viewsets.ModelViewSet):
    """
    Manage finishing process prices for a shop.
    Endpoint: /api/shops/{shop_slug}/pricing/finishing/
    """
    
    def get_serializer_class(self):
        if self.action == "list":
            return FinishingPriceListSerializer
        return FinishingPriceSerializer
    
    def get_queryset(self):
        return FinishingPrice.objects.filter(
            shop=self.get_shop()
        ).order_by("category", "process_name")
    
    @action(detail=False, methods=["get"])
    def by_category(self, request, shop_slug=None):
        """Group finishing prices by category."""
        shop = self.get_shop()
        prices = FinishingPrice.objects.filter(shop=shop, is_active=True)
        
        grouped = {}
        for price in prices:
            category = price.get_category_display()
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(FinishingPriceListSerializer(price).data)
        
        return Response(grouped)


# =============================================================================
# Volume Discount ViewSet
# =============================================================================

class VolumeDiscountViewSet(ShopScopedMixin, viewsets.ModelViewSet):
    """
    Manage volume discounts for a shop.
    Endpoint: /api/shops/{shop_slug}/pricing/discounts/
    """
    
    serializer_class = VolumeDiscountSerializer
    
    def get_queryset(self):
        return VolumeDiscount.objects.filter(
            shop=self.get_shop()
        ).order_by("minimum_quantity")


# =============================================================================
# Rate Card View (Read-Only Composite View)
# =============================================================================

class RateCardView(APIView):
    """
    Generate a complete Rate Card for a shop.
    Endpoint: GET /api/shops/{shop_slug}/pricing/rate-card/
    
    This provides a comprehensive view of all pricing in a readable format.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsShopMember]
    
    def get(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug)
        
        # Check permissions
        self.check_object_permissions(request, shop)
        
        # Gather all data
        machines = Machine.objects.filter(shop=shop, is_active=True)
        materials = Material.objects.filter(shop=shop, is_active=True)
        finishing = FinishingPrice.objects.filter(shop=shop, is_active=True)
        discounts = VolumeDiscount.objects.filter(shop=shop, is_active=True)
        
        # Build context for nested serializers
        context = {"request": request, "shop": shop}
        
        # Serialize
        rate_card_data = {
            "shop_name": shop.name,
            "shop_slug": shop.slug,
            "generated_at": timezone.now(),
            "machines": MachinePriceCardSerializer(
                machines, many=True, context=context
            ).data,
            "materials": MaterialPriceCardSerializer(
                materials, many=True, context=context
            ).data,
            "finishing_services": FinishingPriceListSerializer(
                finishing, many=True
            ).data,
            "volume_discounts": VolumeDiscountSerializer(
                discounts, many=True
            ).data,
        }
        
        # Add summary
        rate_card_data["summary"] = {
            "total_machines": len(rate_card_data["machines"]),
            "total_materials": len(rate_card_data["materials"]),
            "total_finishing_services": len(rate_card_data["finishing_services"]),
            "total_volume_discounts": len(rate_card_data["volume_discounts"]),
        }
        
        return Response(rate_card_data)


# =============================================================================
# Cost Calculator View
# =============================================================================

class CostCalculatorView(APIView):
    """
    Calculate job costs based on pricing configuration.
    Endpoint: POST /api/shops/{shop_slug}/pricing/calculate/
    
    Accepts job parameters and returns detailed cost breakdown.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsShopMember]
    
    def post(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug)
        self.check_object_permissions(request, shop)
        
        # Validate input
        input_serializer = PrintCostCalculatorSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data
        
        breakdown = {}
        
        # 1. Calculate print cost
        try:
            print_price = DigitalPrintPrice.objects.get(
                shop=shop,
                machine_id=data["machine_id"],
                sheet_size=data["sheet_size"],
                color_mode=data["color_mode"],
                is_active=True
            )
            print_cost = print_price.calculate_cost(
                quantity=data["quantity"],
                duplex=data["duplex"]
            )
            breakdown["print"] = {
                "rate": str(print_price.effective_duplex_rate if data["duplex"] else print_price.click_rate),
                "quantity": data["quantity"],
                "duplex": data["duplex"],
                "subtotal": str(print_cost),
            }
        except DigitalPrintPrice.DoesNotExist:
            return Response(
                {"error": "No pricing found for the specified machine/size/color configuration"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. Calculate material cost (if specified)
        material_cost = Decimal("0")
        if data.get("material_id"):
            try:
                material_price = MaterialPrice.objects.get(
                    shop=shop,
                    material_id=data["material_id"],
                    is_active=True
                )
                material_cost = material_price.calculated_selling_price * data["quantity"]
                breakdown["material"] = {
                    "name": material_price.material.name,
                    "unit_price": str(material_price.calculated_selling_price),
                    "quantity": data["quantity"],
                    "subtotal": str(material_cost),
                }
            except MaterialPrice.DoesNotExist:
                pass
        
        # 3. Calculate finishing costs
        finishing_cost = Decimal("0")
        finishing_breakdown = []
        for finishing_id in data.get("finishing_ids", []):
            try:
                finishing = FinishingPrice.objects.get(
                    shop=shop,
                    id=finishing_id,
                    is_active=True
                )
                cost = finishing.calculate_cost(quantity=data["quantity"])
                finishing_cost += cost
                finishing_breakdown.append({
                    "name": finishing.process_name,
                    "unit_price": str(finishing.price),
                    "setup_fee": str(finishing.setup_fee),
                    "subtotal": str(cost),
                })
            except FinishingPrice.DoesNotExist:
                continue
        
        if finishing_breakdown:
            breakdown["finishing"] = finishing_breakdown
        
        # 4. Calculate subtotal
        subtotal = print_cost + material_cost + finishing_cost
        
        # 5. Apply volume discounts
        discount_amount = Decimal("0")
        applicable_discount = VolumeDiscount.objects.filter(
            shop=shop,
            is_active=True,
            applies_to_print=True,
            minimum_quantity__lte=data["quantity"]
        ).filter(
            models.Q(maximum_quantity__isnull=True) |
            models.Q(maximum_quantity__gte=data["quantity"])
        ).order_by("-minimum_quantity").first()
        
        if applicable_discount:
            discounted_subtotal = applicable_discount.apply_discount(subtotal)
            discount_amount = subtotal - discounted_subtotal
            breakdown["discount"] = {
                "name": applicable_discount.name,
                "type": applicable_discount.get_discount_type_display(),
                "value": str(applicable_discount.discount_value),
                "amount": str(discount_amount),
            }
        
        # 6. Calculate total
        total = subtotal - discount_amount
        
        result = {
            "print_cost": str(print_cost),
            "material_cost": str(material_cost) if material_cost else None,
            "finishing_cost": str(finishing_cost),
            "subtotal": str(subtotal),
            "discount_amount": str(discount_amount),
            "total": str(total),
            "breakdown": breakdown,
        }
        
        return Response(result)


# =============================================================================
# Price Comparison View
# =============================================================================

class PriceComparisonView(APIView):
    """
    Compare prices across different configurations.
    Endpoint: POST /api/shops/{shop_slug}/pricing/compare/
    
    Useful for showing clients different options.
    """
    
    permission_classes = [permissions.IsAuthenticated, IsShopMember]
    
    def post(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug)
        self.check_object_permissions(request, shop)
        
        quantity = request.data.get("quantity", 100)
        sheet_size = request.data.get("sheet_size", "A4")
        
        # Get all print prices for comparison
        prices = DigitalPrintPrice.objects.filter(
            shop=shop,
            sheet_size=sheet_size,
            is_active=True
        ).select_related("machine")
        
        comparisons = []
        for price in prices:
            single_cost = price.calculate_cost(1, duplex=False)
            bulk_cost = price.calculate_cost(quantity, duplex=False)
            
            comparisons.append({
                "machine": price.machine.name,
                "color_mode": price.get_color_mode_display(),
                "click_rate": str(price.click_rate),
                "cost_for_1": str(single_cost),
                f"cost_for_{quantity}": str(bulk_cost),
                "cost_per_unit_at_volume": str(bulk_cost / quantity),
            })
        
        return Response({
            "sheet_size": sheet_size,
            "quantity": quantity,
            "comparisons": comparisons,
        })


# =============================================================================
# Simple/Customer-Friendly Pricing Views
# =============================================================================

class PaperGSMPriceViewSet(ShopScopedMixin, viewsets.ModelViewSet):
    """
    Manage simple paper GSM prices for a shop.
    Endpoint: /api/shops/{shop_slug}/pricing/paper-gsm/
    
    This is the customer-friendly pricing model:
    - 130 GSM = KES 10
    - 150 GSM = KES 15
    - 200 GSM = KES 20
    - 300 GSM = KES 30
    """
    
    def get_serializer_class(self):
        if self.action == "list":
            return PaperGSMPriceListSerializer
        return PaperGSMPriceSerializer
    
    def get_queryset(self):
        return PaperGSMPrice.objects.filter(
            shop=self.get_shop()
        ).order_by("sheet_size", "paper_type", "gsm")
    
    @action(detail=False, methods=["get"])
    def by_size(self, request, shop_slug=None):
        """Group paper prices by sheet size for easier viewing."""
        shop = self.get_shop()
        prices = PaperGSMPrice.objects.filter(
            shop=shop, is_active=True
        ).order_by("sheet_size", "paper_type", "gsm")
        
        grouped = {}
        for price in prices:
            size = price.sheet_size
            paper_type = price.paper_type
            
            if size not in grouped:
                grouped[size] = {}
            if paper_type not in grouped[size]:
                grouped[size][paper_type] = []
            
            grouped[size][paper_type].append({
                "gsm": price.gsm,
                "price": str(price.price_per_sheet),
            })
        
        return Response(grouped)


class SimpleRateCardView(APIView):
    """
    Customer-friendly rate card showing simple pricing.
    Endpoint: GET /api/shops/{shop_slug}/pricing/simple-rate-card/
    
    Shows:
    - Print prices per side (e.g., A3 Color = KES 15/side)
    - Paper prices by GSM (e.g., 130gsm = KES 10, 300gsm = KES 30)
    - Simple calculation formula
    - Example calculations
    
    This is what customers can see to understand pricing at a glance.
    """
    
    permission_classes = [permissions.AllowAny]  # Public rate card
    
    def get(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug)
        
        # 1. Get print prices (grouped by size/color)
        print_prices = DigitalPrintPrice.objects.filter(
            shop=shop, is_active=True
        ).order_by("sheet_size", "color_mode")
        
        print_price_list = []
        for pp in print_prices:
            print_price_list.append({
                "sheet_size": pp.sheet_size,
                "sheet_size_display": pp.get_sheet_size_display(),
                "color_mode": pp.color_mode,
                "color_mode_display": pp.get_color_mode_display(),
                "price_per_side": str(pp.click_rate),
                "price_double_sided": str(pp.effective_duplex_rate),
            })
        
        # 2. Get paper prices (grouped by size, then paper type)
        paper_prices = PaperGSMPrice.objects.filter(
            shop=shop, is_active=True
        ).order_by("sheet_size", "paper_type", "gsm")
        
        paper_price_dict = {}
        for gp in paper_prices:
            size = gp.sheet_size
            paper_type = gp.paper_type
            
            if size not in paper_price_dict:
                paper_price_dict[size] = {}
            if paper_type not in paper_price_dict[size]:
                paper_price_dict[size][paper_type] = []
            
            paper_price_dict[size][paper_type].append({
                "gsm": gp.gsm,
                "price": str(gp.price_per_sheet),
            })
        
        # 3. Generate examples
        examples = []
        
        # Find an A3 color print price for examples
        a3_print = print_prices.filter(sheet_size="A3", color_mode="COLOR").first()
        a3_paper_300 = paper_prices.filter(sheet_size="A3", gsm=300).first()
        
        if a3_print and a3_paper_300:
            single_total = a3_print.click_rate + a3_paper_300.price_per_sheet
            double_total = a3_print.effective_duplex_rate + a3_paper_300.price_per_sheet
            
            examples.append({
                "description": "1x A3 single-sided on 300gsm",
                "calculation": f"Print ({a3_print.click_rate} × 1 side) + Paper ({a3_paper_300.price_per_sheet}) = KES {single_total}",
                "total": str(single_total),
            })
            examples.append({
                "description": "1x A3 double-sided on 300gsm", 
                "calculation": f"Print ({a3_print.click_rate} × 2 sides) + Paper ({a3_paper_300.price_per_sheet}) = KES {double_total}",
                "total": str(double_total),
            })
            examples.append({
                "description": "100x A3 double-sided on 300gsm",
                "calculation": f"(Print {a3_print.effective_duplex_rate} + Paper {a3_paper_300.price_per_sheet}) × 100 = KES {double_total * 100}",
                "total": str(double_total * 100),
            })
        
        return Response({
            "shop_name": shop.name,
            "generated_at": timezone.now(),
            "print_prices": print_price_list,
            "paper_prices": paper_price_dict,
            "how_to_calculate": "Total per sheet = (Print price × sides) + Paper price. Multiply by quantity for total.",
            "examples": examples,
        })


class SimplePriceCalculatorView(APIView):
    """
    Simple price calculator for customers.
    Endpoint: POST /api/shops/{shop_slug}/pricing/simple-calculate/
    
    Input:
    {
        "sheet_size": "A3",
        "gsm": 300,
        "paper_type": "Gloss",
        "sides": 2,
        "quantity": 100,
        "color_mode": "COLOR"
    }
    
    Output:
    {
        "print_price_per_side": 15,
        "print_price_per_sheet": 30,  // 15 × 2 sides
        "paper_price_per_sheet": 30,  // 300gsm paper
        "price_per_sheet": 60,        // 30 + 30
        "total_print_cost": 3000,     // 30 × 100
        "total_paper_cost": 3000,     // 30 × 100
        "total": 6000,                // 60 × 100
        "breakdown_text": "Print: 15 × 2 sides = 30 | Paper (300gsm): 30 | Per sheet: 60 | Total (100 sheets): 6000"
    }
    """
    
    permission_classes = [permissions.AllowAny]  # Public calculator
    
    def post(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug)
        
        # Validate input
        serializer = SimplePriceCalculatorInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        sheet_size = data["sheet_size"]
        gsm = data["gsm"]
        paper_type = data.get("paper_type", "Gloss")
        sides = int(data["sides"])
        quantity = data["quantity"]
        color_mode = data.get("color_mode", "COLOR")
        
        # 1. Get print price
        print_price_obj = DigitalPrintPrice.objects.filter(
            shop=shop,
            sheet_size=sheet_size,
            color_mode=color_mode,
            is_active=True
        ).first()
        
        if not print_price_obj:
            return Response({
                "error": f"No print price found for {sheet_size} {color_mode}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        print_price_per_side = print_price_obj.click_rate
        
        # 2. Get paper price
        paper_price_obj = PaperGSMPrice.objects.filter(
            shop=shop,
            sheet_size=sheet_size,
            gsm=gsm,
            paper_type=paper_type,
            is_active=True
        ).first()
        
        if not paper_price_obj:
            # Try without paper_type filter
            paper_price_obj = PaperGSMPrice.objects.filter(
                shop=shop,
                sheet_size=sheet_size,
                gsm=gsm,
                is_active=True
            ).first()
        
        if not paper_price_obj:
            return Response({
                "error": f"No paper price found for {sheet_size} {gsm}gsm"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        paper_price_per_sheet = paper_price_obj.price_per_sheet
        
        # 3. Calculate
        print_price_per_sheet = print_price_per_side * sides
        price_per_sheet = print_price_per_sheet + paper_price_per_sheet
        
        total_print_cost = print_price_per_sheet * quantity
        total_paper_cost = paper_price_per_sheet * quantity
        total = price_per_sheet * quantity
        
        # 4. Build breakdown text
        breakdown_text = (
            f"Print: {print_price_per_side} × {sides} side(s) = {print_price_per_sheet} | "
            f"Paper ({gsm}gsm): {paper_price_per_sheet} | "
            f"Per sheet: {price_per_sheet} | "
            f"Total ({quantity} sheets): {total}"
        )
        
        return Response({
            "sheet_size": sheet_size,
            "gsm": gsm,
            "paper_type": paper_type,
            "sides": sides,
            "quantity": quantity,
            "print_price_per_side": str(print_price_per_side),
            "print_price_per_sheet": str(print_price_per_sheet),
            "paper_price_per_sheet": str(paper_price_per_sheet),
            "price_per_sheet": str(price_per_sheet),
            "total_print_cost": str(total_print_cost),
            "total_paper_cost": str(total_paper_cost),
            "total": str(total),
            "breakdown_text": breakdown_text,
        })