# shops/urls.py

"""
URL configuration for the shops app.

Includes routes for:
- Shop CRUD
- Shop members/team management
- Opening hours management
- Shop social links
- Shop claims
- Nearby shops search
- Inventory (machines, materials)
- Pricing
- Quotes and Product Templates
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    NearbyShopsView,
    OpeningHoursViewSet,
    ShopClaimAdminUpdateView,
    ShopClaimVerifyView,
    ShopClaimViewSet,
    ShopMemberViewSet,
    ShopSocialLinkViewSet,
    ShopViewSet,
)

# Import quote patterns
from quotes.urls import shop_quote_patterns

# Import public pricing views
from pricing.views import RateCardView, CalculatePriceView

# Import shop-scoped template views
from templates.views_shop import ShopTemplateCategoryViewSet, ShopPrintTemplateViewSet

app_name = "shops"

# Main router for shops and claims
router = DefaultRouter()
router.register(r"shops", ShopViewSet, basename="shop")
router.register(r"claims", ShopClaimViewSet, basename="claim")

urlpatterns = [
    # Main router URLs
    path("", include(router.urls)),
    
    # Nested shop resources (using explicit paths instead of nested routers)
    path(
        "shops/<slug:shop_slug>/members/",
        ShopMemberViewSet.as_view({"get": "list", "post": "create"}),
        name="shop-members-list",
    ),
    path(
        "shops/<slug:shop_slug>/members/<int:pk>/",
        ShopMemberViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="shop-members-detail",
    ),
    
    path(
        "shops/<slug:shop_slug>/hours/",
        OpeningHoursViewSet.as_view({"get": "list", "post": "create"}),
        name="shop-hours-list",
    ),
    path(
        "shops/<slug:shop_slug>/hours/bulk/",
        OpeningHoursViewSet.as_view({"post": "bulk_update"}),
        name="shop-hours-bulk",
    ),
    path(
        "shops/<slug:shop_slug>/hours/<int:pk>/",
        OpeningHoursViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="shop-hours-detail",
    ),
    
    path(
        "shops/<slug:shop_slug>/social-links/",
        ShopSocialLinkViewSet.as_view({"get": "list", "post": "create"}),
        name="shop-social-links-list",
    ),
    path(
        "shops/<slug:shop_slug>/social-links/<int:pk>/",
        ShopSocialLinkViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="shop-social-links-detail",
    ),
    
    # Claim verification (public endpoint)
    path("claims/verify/", ShopClaimVerifyView.as_view(), name="claim-verify"),
    
    # Admin claim review
    path("claims/<int:pk>/review/", ShopClaimAdminUpdateView.as_view(), name="claim-review"),
    
    # Nearby shops search
    path("shops-nearby/", NearbyShopsView.as_view(), name="shops-nearby"),
    
    # Public pricing endpoints (no auth required)
    path("shops/<slug:shop_slug>/rate-card/", RateCardView.as_view(), name="shop-rate-card"),
    path("shops/<slug:shop_slug>/calculate-price/", CalculatePriceView.as_view(), name="shop-calculate-price"),
    
    # Shop-scoped template endpoints (AllowAny for public browsing)
    path(
        "shops/<slug:shop_slug>/template-categories/",
        ShopTemplateCategoryViewSet.as_view({"get": "list"}),
        name="shop-template-categories-list",
    ),
    path(
        "shops/<slug:shop_slug>/template-categories/<slug:slug>/",
        ShopTemplateCategoryViewSet.as_view({"get": "retrieve"}),
        name="shop-template-categories-detail",
    ),
    path(
        "shops/<slug:shop_slug>/templates/",
        ShopPrintTemplateViewSet.as_view({"get": "list"}),
        name="shop-templates-list",
    ),
    path(
        "shops/<slug:shop_slug>/templates/<slug:template_slug>/",
        ShopPrintTemplateViewSet.as_view({"get": "retrieve"}),
        name="shop-templates-detail",
    ),
    path(
        "shops/<slug:shop_slug>/templates/<slug:template_slug>/calculate-price/",
        ShopPrintTemplateViewSet.as_view({"post": "calculate_price"}),
        name="shop-templates-calculate-price",
    ),
    path(
        "shops/<slug:shop_slug>/templates/<slug:template_slug>/create-quote/",
        ShopPrintTemplateViewSet.as_view({"post": "create_quote"}),
        name="shop-templates-create-quote",
    ),
]

# Add quote patterns (nested under shops/<slug:shop_slug>/)
for pattern in shop_quote_patterns:
    urlpatterns.append(
        path(f"shops/<slug:shop_slug>/{pattern.pattern}", pattern.callback, name=pattern.name)
    )