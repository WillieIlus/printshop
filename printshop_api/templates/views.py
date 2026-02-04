# templates/views.py

from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from shops.models import Shop
from pricing.models import PaperGSMPrice, DigitalPrintPrice

from .models import (
    TemplateCategory,
    PrintTemplate,
    TemplateFinishing,
    TemplateOption,
)
from .serializers import (
    TemplateCategorySerializer,
    PrintTemplateListSerializer,
    PrintTemplateDetailSerializer,
    TemplateQuoteRequestSerializer,
    TemplatePriceCalculationSerializer,
)


class TemplateCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public API for browsing template categories.
    Endpoint: /api/templates/categories/
    """
    
    queryset = TemplateCategory.objects.filter(is_active=True)
    serializer_class = TemplateCategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    @action(detail=True, methods=["get"])
    def templates(self, request, slug=None):
        """Get all templates in this category."""
        category = self.get_object()
        templates = PrintTemplate.objects.filter(
            category=category,
            is_active=True
        )
        serializer = PrintTemplateListSerializer(templates, many=True)
        return Response(serializer.data)


class PrintTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public API for browsing print templates (gallery).
    Endpoint: /api/templates/
    
    Customers can:
    - List all templates
    - Filter by category
    - Search by title
    - View template details
    - Calculate prices
    - Create quote requests
    """
    
    queryset = PrintTemplate.objects.filter(is_active=True).select_related(
        "category"
    ).prefetch_related(
        "finishing_options",
        "options"
    )
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category__slug", "is_popular", "is_best_value", "is_new"]
    search_fields = ["title", "description", "category__name"]
    ordering_fields = ["base_price", "title", "created_at"]
    ordering = ["category", "title"]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PrintTemplateDetailSerializer
        return PrintTemplateListSerializer

    @action(detail=False, methods=["get"])
    def popular(self, request):
        """Get popular templates."""
        templates = self.queryset.filter(is_popular=True)[:12]
        serializer = PrintTemplateListSerializer(templates, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Get featured templates (popular + best value)."""
        templates = self.queryset.filter(
            is_popular=True
        ) | self.queryset.filter(is_best_value=True)
        templates = templates.distinct()[:12]
        serializer = PrintTemplateListSerializer(templates, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def calculate_price(self, request, slug=None):
        """
        Calculate price for a template with given options.
        This provides real-time price updates as customer changes options.
        
        POST /api/templates/{slug}/calculate-price/
        {
            "shop_id": 1,  // optional
            "quantity": 500,
            "gsm": 300,
            "print_sides": "DUPLEX",
            "selected_option_ids": [1, 2],
            "selected_finishing_ids": [3]
        }
        """
        template = self.get_object()
        serializer = TemplatePriceCalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Get quantity
        quantity = data["quantity"]
        if quantity < template.min_quantity:
            return Response({
                "error": f"Minimum quantity is {template.min_quantity}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Determine GSM and print sides
        gsm = data.get("gsm") or template.default_gsm or 300
        print_sides = data.get("print_sides") or template.default_print_sides or "DUPLEX"
        sides = 2 if print_sides == "DUPLEX" else 1
        
        # Get shop (optional - for shop-specific pricing)
        shop_id = data.get("shop_id")
        shop = None
        if shop_id:
            try:
                shop = Shop.objects.get(id=shop_id, is_active=True)
            except Shop.DoesNotExist:
                pass
        
        # Calculate base price
        base_unit_price = template.base_price
        
        # If shop provided, try to use their actual pricing
        print_price_per_side = Decimal("0")
        paper_price = Decimal("0")
        
        if shop:
            # Get print price
            print_price_obj = DigitalPrintPrice.objects.filter(
                shop=shop,
                sheet_size="A3",  # Default to A3 for templates
                color_mode="COLOR",
                is_active=True
            ).first()
            if print_price_obj:
                print_price_per_side = print_price_obj.click_rate
            
            # Get paper price by GSM
            paper_price_obj = PaperGSMPrice.objects.filter(
                shop=shop,
                sheet_size="A3",
                gsm=gsm,
                is_active=True
            ).first()
            if paper_price_obj:
                paper_price = paper_price_obj.price_per_sheet
        
        # Calculate print and paper costs
        if print_price_per_side > 0 and paper_price > 0:
            # Use actual shop pricing
            print_cost = print_price_per_side * sides
            unit_price = print_cost + paper_price
        else:
            # Fall back to template base price
            unit_price = base_unit_price
        
        # Add option modifiers
        selected_option_ids = data.get("selected_option_ids", [])
        option_modifiers = Decimal("0")
        if selected_option_ids:
            options = TemplateOption.objects.filter(
                id__in=selected_option_ids,
                template=template
            )
            option_modifiers = sum(opt.price_modifier for opt in options)
        
        # Add finishing costs
        selected_finishing_ids = data.get("selected_finishing_ids", [])
        finishing_cost = Decimal("0")
        mandatory_finishing = template.finishing_options.filter(is_mandatory=True)
        
        # Include mandatory finishing
        for finish in mandatory_finishing:
            finishing_cost += finish.price_adjustment
        
        # Include selected optional finishing
        if selected_finishing_ids:
            optional_finishing = template.finishing_options.filter(
                id__in=selected_finishing_ids,
                is_mandatory=False
            )
            for finish in optional_finishing:
                finishing_cost += finish.price_adjustment
        
        # Calculate totals
        unit_total = unit_price + option_modifiers + finishing_cost
        subtotal = unit_total * quantity
        tax_rate = Decimal("16.00")  # 16% VAT
        tax_amount = subtotal * (tax_rate / 100)
        total = subtotal + tax_amount
        
        return Response({
            "template_id": template.id,
            "template_title": template.title,
            "quantity": quantity,
            "gsm": gsm,
            "print_sides": print_sides,
            "pricing": {
                "unit_price": str(unit_price),
                "option_modifiers": str(option_modifiers),
                "finishing_per_unit": str(finishing_cost),
                "unit_total": str(unit_total),
                "subtotal": str(subtotal),
                "tax_rate": str(tax_rate),
                "tax_amount": str(tax_amount),
                "total": str(total),
            },
            "breakdown": {
                "print_price_per_side": str(print_price_per_side) if print_price_per_side else None,
                "paper_price": str(paper_price) if paper_price else None,
                "using_shop_pricing": shop is not None and print_price_per_side > 0,
            }
        })

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def create_quote(self, request, slug=None):
        """
        Create a quote request from this template.
        Requires authentication.
        
        POST /api/templates/{slug}/create-quote/
        {
            "shop_id": 1,
            "quantity": 500,
            "gsm": 300,
            "print_sides": "DUPLEX",
            "selected_option_ids": [1, 2],
            "selected_finishing_ids": [3],
            "customer_notes": "Please use blue ink"
        }
        """
        template = self.get_object()
        serializer = TemplateQuoteRequestSerializer(data={
            **request.data,
            "template_id": template.id
        })
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Get shop
        shop_id = data.get("shop_id")
        if shop_id:
            shop = get_object_or_404(Shop, id=shop_id, is_active=True)
        else:
            # Default to first active shop (in real app, would have better logic)
            shop = Shop.objects.filter(is_active=True).first()
            if not shop:
                return Response({
                    "error": "No shop available"
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate quantity
        quantity = data["quantity"]
        if quantity < template.min_quantity:
            return Response({
                "error": f"Minimum quantity is {template.min_quantity}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create quote
        from quotes.models import Quote, QuoteItem
        
        quote = Quote.objects.create(
            shop=shop,
            user=request.user,
            source_template=template,
            title=f"{template.title} - {quantity} pcs",
            customer_notes=data.get("customer_notes", ""),
            status=Quote.Status.PENDING,
        )
        
        # Create quote item
        gsm = data.get("gsm") or template.default_gsm or 300
        print_sides = data.get("print_sides") or template.default_print_sides
        
        item = QuoteItem.objects.create(
            quote=quote,
            name=template.title,
            quantity=quantity,
        )
        
        # Store configuration in item (simplified - in production would create parts)
        # For now, store as a note
        config_note = f"GSM: {gsm}, Sides: {print_sides}"
        if data.get("selected_option_ids"):
            options = TemplateOption.objects.filter(id__in=data["selected_option_ids"])
            config_note += f", Options: {', '.join(o.label for o in options)}"
        if data.get("selected_finishing_ids"):
            finishes = TemplateFinishing.objects.filter(id__in=data["selected_finishing_ids"])
            config_note += f", Finishing: {', '.join(f.name for f in finishes)}"
        
        quote.internal_notes = config_note
        quote.save()
        
        return Response({
            "message": "Quote request created successfully",
            "quote_id": quote.id,
            "quote_reference": quote.reference,
            "status": quote.status,
        }, status=status.HTTP_201_CREATED)


class TemplateGalleryView(APIView):
    """
    Public gallery view with categories and featured templates.
    Endpoint: GET /api/templates/gallery/
    
    Returns a structured response for rendering the template gallery page.
    """
    
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Get active categories with templates
        categories = TemplateCategory.objects.filter(
            is_active=True
        ).prefetch_related("print_templates")
        
        # Get featured templates
        featured = PrintTemplate.objects.filter(
            is_active=True
        ).filter(
            is_popular=True
        )[:6]
        
        # Build response
        category_data = []
        for cat in categories:
            templates = cat.print_templates.filter(is_active=True)[:8]
            if templates.exists():
                category_data.append({
                    "category": TemplateCategorySerializer(cat).data,
                    "templates": PrintTemplateListSerializer(templates, many=True).data,
                })
        
        return Response({
            "featured": PrintTemplateListSerializer(featured, many=True).data,
            "categories": category_data,
        })
