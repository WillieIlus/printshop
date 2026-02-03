# printshop_api/urls.py

"""
Root URL configuration for the printshop_api project.
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView  # <--- 1. Add this import

urlpatterns = [
    # 2. Add this line to fix the 404 at the root URL
    path("", RedirectView.as_view(url="/api/"), name="root-redirect"),

    path("admin/", admin.site.urls),
    
    # API endpoints
    path("api/", include("accounts.urls", namespace="accounts")),
    path("api/", include("shops.urls", namespace="shops")),
    
    # NOTE: Since we moved machine/material routes into shops/urls.py, 
    # you should remove this line to avoid "ModuleNotFoundError" or duplicate routes:
    # path("api/", include("inventory.urls", namespace="inventory")),
    
    path("api/", include("pricing.urls", namespace="pricing")),

    # Login/Logout for Browsable API
    path("api-auth/", include("rest_framework.urls")), 
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)