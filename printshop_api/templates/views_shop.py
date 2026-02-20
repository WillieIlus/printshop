# templates/views_shop.py
"""
Shop-scoped template views.
Endpoints under /api/shops/<slug>/template-categories/ and /api/shops/<slug>/templates/
"""

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
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
    TemplatePriceCalculationSerializer,
    TemplateQuoteRequestSerializer,
)
from .services.pricing import calculate_template_price
from .services.gsm_validation import validate_gsm_for_calculation


def get_shop_from_kwargs(kwargs):
    """Get active shop by slug from URL kwargs."""
    return get_object_or_404(Shop, slug=kwargs["shop_slug"], is_active=True)


class ShopTemplateCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Shop-scoped template categories.
    GET /api/shops/<slug>/template-categories/
    Returns only categories that have templates for this shop.
    """

    serializer_class = TemplateCategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        shop = get_shop_from_kwargs(self.kwargs)
        # Categories that have at least one active template for this shop
        return TemplateCategory.objects.filter(
            is_active=True,
            print_templates__shop=shop,
            print_templates__is_active=True,
        ).distinct().order_by("display_order", "name")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = get_shop_from_kwargs(self.kwargs)
        return context


class ShopPrintTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Shop-scoped print templates.
    GET /api/shops/<slug>/templates/
    GET /api/shops/<slug>/templates/<template_slug>/
    POST /api/shops/<slug>/templates/<template_slug>/calculate-price/

    AllowAny for public browsing. Only returns templates for this shop.
    """

    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category__slug", "is_popular", "is_best_value", "is_new"]
    search_fields = ["title", "description", "category__name"]
    ordering_fields = ["base_price", "title", "created_at"]
    ordering = ["category", "title"]
    lookup_field = "slug"
    lookup_url_kwarg = "template_slug"

    def get_queryset(self):
        shop = get_shop_from_kwargs(self.kwargs)
        return (
            PrintTemplate.objects.filter(shop=shop, is_active=True)
            .select_related("category", "shop")
            .prefetch_related("finishing_options", "options")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PrintTemplateDetailSerializer
        return PrintTemplateListSerializer

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        return get_object_or_404(queryset, **filter_kwargs)

    @action(detail=True, methods=["post"], url_path="calculate-price")
    def calculate_price(self, request, shop_slug=None, template_slug=None):
        """
        Calculate price for a template. Verifies template belongs to shop.
        Enforces template GSM constraints and shop capability limits.
        """
        template = self.get_object()
        serializer = TemplatePriceCalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        quantity = data["quantity"]
        if quantity < template.min_quantity:
            return Response(
                {"error": f"Minimum quantity is {template.min_quantity}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # GSM validation for digital mode (template constraints + shop capability)
        is_large_format = (
            data.get("unit") == "SQM"
            or data.get("area_sqm") is not None
            or (data.get("width_m") is not None and data.get("height_m") is not None)
            or data.get("material_type") is not None
        )
        if not is_large_format:
            gsm_error = validate_gsm_for_calculation(
                template=template,
                shop=template.shop,
                gsm=data.get("gsm"),
                sheet_size=data.get("sheet_size"),
            )
            if gsm_error:
                return Response(
                    {"error": gsm_error},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        result = calculate_template_price(template, data)
        return Response(result)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def create_quote(self, request, shop_slug=None, template_slug=None):
        """
        Create a quote request from this template. Shop is from URL.
        POST /api/shops/<slug>/templates/<template_slug>/create-quote/
        """
        template = self.get_object()
        serializer = TemplateQuoteRequestSerializer(data={
            **request.data,
            "template_id": template.id,
            "shop_id": template.shop_id,  # Shop from URL
        })
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        quantity = data["quantity"]
        if quantity < template.min_quantity:
            return Response({
                "error": f"Minimum quantity is {template.min_quantity}"
            }, status=status.HTTP_400_BAD_REQUEST)

        from quotes.models import Quote, QuoteItem

        quote = Quote.objects.create(
            shop=template.shop,
            user=request.user,
            source_template=template,
            title=f"{template.title} - {quantity} pcs",
            customer_notes=data.get("customer_notes", ""),
            status=Quote.Status.PENDING,
        )

        gsm = data.get("gsm") or template.default_gsm or 300
        print_sides = data.get("print_sides") or template.default_print_sides

        QuoteItem.objects.create(
            quote=quote,
            name=template.title,
            quantity=quantity,
        )

        config_note = f"GSM: {gsm}, Sides: {print_sides}"
        if data.get("selected_option_ids"):
            options = TemplateOption.objects.filter(
                id__in=data["selected_option_ids"], template=template
            )
            config_note += f", Options: {', '.join(o.label for o in options)}"
        if data.get("selected_finishing_ids"):
            finishes = TemplateFinishing.objects.filter(
                id__in=data["selected_finishing_ids"], template=template
            )
            config_note += f", Finishing: {', '.join(f.name for f in finishes)}"

        quote.internal_notes = config_note
        quote.save()

        return Response({
            "message": "Quote request created successfully",
            "quote_id": quote.id,
            "quote_reference": quote.reference,
            "status": quote.status,
        }, status=status.HTTP_201_CREATED)
