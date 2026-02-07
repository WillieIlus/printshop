# pricing/urls.py
"""
URL patterns for pricing API.

Public endpoints (no auth required):
- GET /api/shops/{slug}/rate-card/ - View rate card
- POST /api/shops/{slug}/calculate-price/ - Calculate price

Shop owner endpoints (auth required):
- /api/shops/{slug}/pricing/printing/ - CRUD printing prices
- /api/shops/{slug}/pricing/paper/ - CRUD paper prices
- /api/shops/{slug}/pricing/finishing/ - CRUD finishing services
- /api/shops/{slug}/pricing/discounts/ - CRUD volume discounts
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = "pricing"

from .views import (
    PrintingPriceViewSet,
    PaperPriceViewSet,
    FinishingServiceViewSet,
    VolumeDiscountViewSet,
    RateCardView,
    CalculatePriceView,
)


# Router for shop-scoped CRUD endpoints
router = DefaultRouter()
router.register(r"printing", PrintingPriceViewSet, basename="printing-price")
router.register(r"paper", PaperPriceViewSet, basename="paper-price")
router.register(r"finishing", FinishingServiceViewSet, basename="finishing-service")
router.register(r"discounts", VolumeDiscountViewSet, basename="volume-discount")


# URL patterns
urlpatterns = [
    # Shop pricing management (authenticated)
    path("", include(router.urls)),
]


# Public URL patterns (to be included at shop level)
public_urlpatterns = [
    path("rate-card/", RateCardView.as_view(), name="rate-card"),
    path("calculate-price/", CalculatePriceView.as_view(), name="calculate-price"),
]
