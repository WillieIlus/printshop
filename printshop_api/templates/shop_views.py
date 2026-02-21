# templates/shop_views.py
"""
Shop-scoped template management views.
Endpoints: /api/shops/{slug}/templates/categories/ and /api/shops/{slug}/templates/
"""

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from shops.models import Shop
from shops.permissions import IsShopOwner

from .models import TemplateCategory, PrintTemplate, TemplateFinishing, TemplateOption
from .serializers import (
    PublicShopTemplateCategorySerializer,
    PublicShopTemplateDetailSerializer,
    PublicShopTemplateListSerializer,
    ShopPrintTemplateCreateUpdateSerializer,
    ShopTemplateCategorySerializer,
    ShopPrintTemplateSerializer,
    TemplatePriceCalculationSerializer,
)
from .services.pricing import calculate_template_price


class ShopTemplateCategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD for template categories scoped to a shop.
    GET /api/shops/{slug}/templates/categories/ or /api/shops/{slug}/template-categories/
    Public list/retrieve: AllowAny. Create/update/delete: IsShopOwner.
    Returns categories even when 0 templates (templates_count per category).
    """
    serializer_class = ShopTemplateCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsShopOwner]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "slug"]
    ordering_fields = ["display_order", "name"]
    ordering = ["display_order", "name"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsShopOwner()]

    def get_shop(self) -> Shop:
        if not hasattr(self, "_shop"):
            if self.action in ["list", "retrieve"]:
                self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"], is_active=True)
            else:
                self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return self._shop

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return PublicShopTemplateCategorySerializer
        return ShopTemplateCategorySerializer

    def get_queryset(self):
        return TemplateCategory.objects.filter(
            shop=self.get_shop(),
            is_active=True,
        ).order_by("display_order", "name")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = self.get_shop()
        return context

    def perform_create(self, serializer):
        serializer.save(shop=self.get_shop())

    def check_object_permissions(self, request, obj):
        if self.action in ["list", "retrieve"]:
            return
        super().check_object_permissions(request, obj)
        if obj.shop_id != self.get_shop().pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Template category does not belong to this shop.")


class ShopPrintTemplateViewSet(viewsets.ModelViewSet):
    """
    CRUD for print templates scoped to a shop.
    GET /api/shops/{slug}/templates/ - Public list (AllowAny)
    GET /api/shops/{slug}/templates/{slug}/ - Public detail (AllowAny)
    POST /api/shops/{slug}/templates/{slug}/calculate-price/ - Public (AllowAny)
    Create/update/delete: IsShopOwner.
    """
    permission_classes = [permissions.IsAuthenticated, IsShopOwner]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category__slug", "is_active"]
    search_fields = ["title", "slug", "description"]
    ordering_fields = ["title", "base_price", "min_quantity", "created_at"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action in ["list", "retrieve", "calculate_price"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsShopOwner()]

    def get_shop(self) -> Shop:
        if not hasattr(self, "_shop"):
            if self.action in ["list", "retrieve", "calculate_price"]:
                self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"], is_active=True)
            else:
                self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return self._shop

    def get_queryset(self):
        qs = PrintTemplate.objects.filter(shop=self.get_shop()).select_related(
            "category", "shop"
        ).prefetch_related("finishing_options", "options")
        if self.action in ["list", "retrieve"]:
            qs = qs.filter(is_active=True)
        return qs

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ShopPrintTemplateCreateUpdateSerializer
        if self.action == "retrieve":
            return PublicShopTemplateDetailSerializer
        if self.action == "list":
            return PublicShopTemplateListSerializer
        return ShopPrintTemplateSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = self.get_shop()
        return context

    def perform_create(self, serializer):
        serializer.save(shop=self.get_shop())

    def check_object_permissions(self, request, obj):
        if self.action in ["list", "retrieve", "calculate_price"]:
            return
        super().check_object_permissions(request, obj)
        if obj.shop_id != self.get_shop().pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Template does not belong to this shop.")

    @action(detail=True, methods=["post"], url_path="calculate-price")
    def calculate_price(self, request, shop_slug=None, slug=None):
        """
        Calculate price for this template.
        POST /api/shops/{slug}/templates/{template_slug}/calculate-price/
        Validates: quantity >= min_quantity, gsm within template constraints.
        Returns: breakdown (printing/material/finishing/total), imposition fields, notes.
        """
        template = self.get_object()
        serializer = TemplatePriceCalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data["quantity"] < template.min_quantity:
            return Response(
                {"error": f"Minimum quantity is {template.min_quantity}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate GSM within template constraints (for digital mode)
        gsm = data.get("gsm")
        if gsm is not None and not (
            data.get("unit") == "SQM"
            or data.get("area_sqm") is not None
            or (data.get("width_m") and data.get("height_m"))
        ):
            if template.min_gsm is not None and gsm < template.min_gsm:
                return Response(
                    {"error": f"GSM must be at least {template.min_gsm}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if template.max_gsm is not None and gsm > template.max_gsm:
                return Response(
                    {"error": f"GSM must be at most {template.max_gsm}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        result = calculate_template_price(template, data)
        return Response(result)
