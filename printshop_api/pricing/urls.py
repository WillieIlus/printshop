# pricing/urls.py
"""
URL patterns for pricing API.

Public endpoints (no auth required):
- GET /api/shops/{slug}/rate-card/ - View rate card
- POST /api/shops/{slug}/calculate-price/ - Calculate price
- GET /api/pricing/defaults/printing/ - Default printing templates
- GET /api/pricing/defaults/papers/ - Default paper templates
- GET /api/pricing/defaults/materials/ - Default material templates
- GET /api/pricing/defaults/finishing/ - Default finishing templates

Shop owner endpoints (auth required):
- /api/shops/{slug}/pricing/printing/ - CRUD printing prices
- /api/shops/{slug}/pricing/paper/ - CRUD paper prices
- /api/shops/{slug}/pricing/material/ - CRUD material prices
- /api/shops/{slug}/pricing/finishing/ - CRUD finishing services
- /api/shops/{slug}/pricing/discounts/ - CRUD volume discounts
- POST /api/shops/{slug}/pricing/seed-defaults/ - Seed from templates
- GET /api/shops/{slug}/pricing/status/ - Pricing status counts
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = "pricing"

from .views import (
    PrintingPriceViewSet,
    PaperPriceViewSet,
    MaterialPriceViewSet,
    FinishingServiceViewSet,
    VolumeDiscountViewSet,
    SeedDefaultsView,
    PricingStatusView,
    RateCardView,
    CalculatePriceView,
)


# Router for shop-scoped CRUD endpoints
router = DefaultRouter()
router.register(r"printing", PrintingPriceViewSet, basename="printing-price")
router.register(r"paper", PaperPriceViewSet, basename="paper-price")
router.register(r"material", MaterialPriceViewSet, basename="material-price")
router.register(r"finishing", FinishingServiceViewSet, basename="finishing-service")
router.register(r"discounts", VolumeDiscountViewSet, basename="volume-discount")


# URL patterns for shop-scoped pricing (under /api/shops/<slug>/pricing/)
urlpatterns = [
    path("", include(router.urls)),
    path("seed-defaults/", SeedDefaultsView.as_view(), name="seed-defaults"),
    path("status/", PricingStatusView.as_view(), name="pricing-status"),
]


# Public URL patterns (to be included at shop level)
public_urlpatterns = [
    path("rate-card/", RateCardView.as_view(), name="rate-card"),
    path("calculate-price/", CalculatePriceView.as_view(), name="calculate-price"),
]


