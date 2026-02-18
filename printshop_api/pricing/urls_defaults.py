# pricing/urls_defaults.py
"""URL patterns for public default pricing templates."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DefaultPrintingPriceTemplateViewSet,
    DefaultPaperPriceTemplateViewSet,
    DefaultMaterialPriceTemplateViewSet,
    DefaultFinishingServiceTemplateViewSet,
)

defaults_router = DefaultRouter()
defaults_router.register(r"printing", DefaultPrintingPriceTemplateViewSet, basename="default-printing")
defaults_router.register(r"papers", DefaultPaperPriceTemplateViewSet, basename="default-papers")
defaults_router.register(r"materials", DefaultMaterialPriceTemplateViewSet, basename="default-materials")
defaults_router.register(r"finishing", DefaultFinishingServiceTemplateViewSet, basename="default-finishing")

urlpatterns = [
    path("defaults/", include(defaults_router.urls)),
]
