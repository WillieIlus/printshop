# templates/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    TemplateCategoryViewSet,
    PrintTemplateViewSet,
    TemplateGalleryView,
)

app_name = "templates"

router = DefaultRouter()
router.register(r"categories", TemplateCategoryViewSet, basename="category")
router.register(r"", PrintTemplateViewSet, basename="template")

urlpatterns = [
    # Gallery overview
    path("gallery/", TemplateGalleryView.as_view(), name="gallery"),
] + router.urls
