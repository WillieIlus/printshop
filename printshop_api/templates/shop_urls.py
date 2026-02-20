# templates/shop_urls.py
"""
URL patterns for shop-scoped template management.
Included at: /api/shops/<slug:shop_slug>/templates/
"""

from django.urls import path

from .shop_views import ShopTemplateCategoryViewSet, ShopPrintTemplateViewSet

app_name = "templates_shop"

urlpatterns = [
    path(
        "categories/",
        ShopTemplateCategoryViewSet.as_view({
            "get": "list",
            "post": "create",
        }),
        name="categories-list",
    ),
    path(
        "categories/<slug:slug>/",
        ShopTemplateCategoryViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }),
        name="categories-detail",
    ),
    path(
        "",
        ShopPrintTemplateViewSet.as_view({
            "get": "list",
            "post": "create",
        }),
        name="templates-list",
    ),
    path(
        "<slug:slug>/calculate-price/",
        ShopPrintTemplateViewSet.as_view({"post": "calculate_price"}),
        name="templates-calculate-price",
    ),
    path(
        "<slug:slug>/",
        ShopPrintTemplateViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }),
        name="templates-detail",
    ),
]
