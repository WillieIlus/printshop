# quotes/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ProductTemplateViewSet,
    QuoteViewSet,
    QuoteItemViewSet,
    CustomerQuoteRequestView,
    MyQuotesViewSet,
)

app_name = "quotes"

# =============================================================================
# Shop-scoped URL patterns (nested under /api/shops/{shop_slug}/)
# =============================================================================

# Product Templates
product_template_list = ProductTemplateViewSet.as_view({
    "get": "list",
    "post": "create"
})
product_template_detail = ProductTemplateViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})

# Quotes
quote_list = QuoteViewSet.as_view({
    "get": "list",
    "post": "create"
})
quote_detail = QuoteViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})
quote_calculate = QuoteViewSet.as_view({
    "post": "calculate"
})
quote_update_status = QuoteViewSet.as_view({
    "post": "update_status"
})
quote_duplicate = QuoteViewSet.as_view({
    "post": "duplicate"
})

# Quote Items
quote_item_list = QuoteItemViewSet.as_view({
    "get": "list",
    "post": "create"
})
quote_item_detail = QuoteItemViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})

# Shop-scoped patterns (to be included in shops/urls.py)
shop_quote_patterns = [
    # Product Templates
    path("product-templates/", product_template_list, name="product-template-list"),
    path("product-templates/<int:pk>/", product_template_detail, name="product-template-detail"),
    
    # Quotes
    path("quotes/", quote_list, name="quote-list"),
    path("quotes/<int:pk>/", quote_detail, name="quote-detail"),
    path("quotes/<int:pk>/calculate/", quote_calculate, name="quote-calculate"),
    path("quotes/<int:pk>/update-status/", quote_update_status, name="quote-update-status"),
    path("quotes/<int:pk>/duplicate/", quote_duplicate, name="quote-duplicate"),
    
    # Quote Items (nested under quotes)
    path("quotes/<int:quote_id>/items/", quote_item_list, name="quote-item-list"),
    path("quotes/<int:quote_id>/items/<int:pk>/", quote_item_detail, name="quote-item-detail"),
    
    # Public quote request
    path("request-quote/", CustomerQuoteRequestView.as_view(), name="request-quote"),
]

# =============================================================================
# User-scoped URL patterns (for /api/my-quotes/)
# =============================================================================

my_quotes_list = MyQuotesViewSet.as_view({
    "get": "list"
})
my_quotes_detail = MyQuotesViewSet.as_view({
    "get": "retrieve"
})
my_quotes_accept = MyQuotesViewSet.as_view({
    "post": "accept"
})
my_quotes_reject = MyQuotesViewSet.as_view({
    "post": "reject"
})

my_quotes_patterns = [
    path("", my_quotes_list, name="my-quotes-list"),
    path("<int:pk>/", my_quotes_detail, name="my-quotes-detail"),
    path("<int:pk>/accept/", my_quotes_accept, name="my-quotes-accept"),
    path("<int:pk>/reject/", my_quotes_reject, name="my-quotes-reject"),
]
