# templates/views.py

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from shops.models import Shop

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
from .services.pricing import calculate_template_price


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
        "category",
        "created_by_shop",
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

    @action(detail=True, methods=["get"], url_path="constraints")
    def constraints(self, request, slug=None):
        """
        Get template GSM constraints and shop capability constraints (if created_by_shop exists).

        GET /api/templates/{slug}/constraints/

        Returns:
        {
            "template": {"min_gsm": 250, "max_gsm": 350, "allowed_gsm_values": null},
            "shop_capabilities": [{"sheet_size": "A4", "min_gsm": null, "max_gsm": 300}, ...]
        }
        """
        template = self.get_object()
        data = {
            "template": {
                "min_gsm": template.min_gsm,
                "max_gsm": template.max_gsm,
                "allowed_gsm_values": template.allowed_gsm_values,
            }
        }
        shop_capabilities = []
        if template.created_by_shop_id:
            from shops.models import ShopPaperCapability

            caps = ShopPaperCapability.objects.filter(
                shop=template.created_by_shop
            ).order_by("sheet_size")
            for cap in caps:
                shop_capabilities.append({
                    "sheet_size": cap.sheet_size,
                    "min_gsm": cap.min_gsm,
                    "max_gsm": cap.max_gsm,
                })
        data["shop_capabilities"] = shop_capabilities
        return Response(data)

    @action(detail=True, methods=["post"], url_path="calculate-price")
    def calculate_price(self, request, slug=None):
        """
        Calculate price for a template with given options.
        Uses STRATEGY 1: base_price + deltas (public demo, no shop-specific pricing).

        POST /api/templates/{slug}/calculate-price/

        Digital mode:
        {
            "quantity": 500,
            "sheet_size": "A3",
            "print_sides": "DUPLEX",
            "gsm": 300,
            "paper_type": "GLOSS",
            "selected_option_ids": [1, 2],
            "selected_finishing_ids": [3]
        }

        Large format mode:
        {
            "quantity": 10,
            "unit": "SQM",
            "width_m": 2.0,
            "height_m": 1.0,
            "material_type": "BANNER",
            "selected_finishing_ids": []
        }

        Returns:
        {
            "printing": {"amount": "KES", "details": {...}},
            "material": {"amount": "KES", "details": {...}},
            "finishing": {"amount": "KES", "items": [...]},
            "subtotal": "KES",
            "total": "KES",
            "notes": ["Demo estimate only", ...]
        }
        """
        template = self.get_object()
        serializer = TemplatePriceCalculationSerializer(
            data=request.data,
            context={"template": template},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        quantity = data["quantity"]
        if quantity < template.min_quantity:
            return Response(
                {"error": f"Minimum quantity is {template.min_quantity}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = calculate_template_price(template, data)
        return Response(result)

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
