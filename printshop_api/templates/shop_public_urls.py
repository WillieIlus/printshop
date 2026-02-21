"""
Public gallery URL patterns for shop-scoped templates.
Included at: /api/shops/<slug:shop_slug>/template-categories/

These endpoints are AllowAny for public browsing.
"""

from django.urls import path

from .shop_views import ShopTemplateCategoryViewSet

app_name = "templates_public"

urlpatterns = [
    path(
        "",
        ShopTemplateCategoryViewSet.as_view({"get": "list"}),
        name="categories-list",
    ),
    path(
        "<slug:slug>/",
        ShopTemplateCategoryViewSet.as_view({"get": "retrieve"}),
        name="categories-detail",
    ),
]
