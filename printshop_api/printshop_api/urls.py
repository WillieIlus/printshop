# printshop_api/urls.py

"""
Root URL configuration for the printshop_api project.

API Structure:
- /api/auth/           - Authentication (login, register, tokens)
- /api/users/          - User management
- /api/shops/          - Shop CRUD and nested resources
- /api/shops/{slug}/   - Shop-specific resources:
    - /members/        - Team management
    - /hours/          - Opening hours
    - /social-links/   - Social media
    - /machines/       - Inventory machines
    - /materials/      - Inventory materials  
    - /pricing/        - Shop pricing
    - /quotes/         - Quote management
    - /product-templates/ - Shop templates
- /api/templates/      - Public template gallery
- /api/my-quotes/      - Customer's quotes
- /api/claims/         - Shop ownership claims
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

# Import my-quotes patterns
from quotes.urls import my_quotes_patterns

urlpatterns = [
    # Root redirect
    path("", RedirectView.as_view(url="/api/"), name="root-redirect"),

    # Admin
    path("admin/", admin.site.urls),
    
    # API endpoints
    path("api/", include("accounts.urls", namespace="accounts")),
    path("api/", include("shops.urls", namespace="shops")),
    path("api/", include("subscription.urls", namespace="subscription")),
    path("api/", include("inventory.urls", namespace="inventory")),
    path("api/shops/<slug:shop_slug>/pricing/", include("pricing.urls", namespace="pricing")),
    
    # Public template gallery
    path("api/templates/", include("templates.urls", namespace="templates")),
    
    # Customer's quotes (authenticated)
    path("api/my-quotes/", include((my_quotes_patterns, "quotes"), namespace="my-quotes")),

    # Login/Logout for Browsable API
    path("api-auth/", include("rest_framework.urls")), 
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)