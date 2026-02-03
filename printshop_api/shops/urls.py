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
]