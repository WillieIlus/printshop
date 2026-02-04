# pricing/urls.py

from django.urls import path
from .views import (
    DigitalPrintPriceViewSet,
    MaterialPriceViewSet,
    FinishingPriceViewSet,
    VolumeDiscountViewSet,
    RateCardView,
    CostCalculatorView,
    PriceComparisonView,
    # Simple/Customer-friendly pricing
    PaperGSMPriceViewSet,
    SimpleRateCardView,
    SimplePriceCalculatorView,
)

app_name = "pricing"

# ViewSet action mappings
print_price_list = DigitalPrintPriceViewSet.as_view({
    "get": "list",
    "post": "create"
})
print_price_detail = DigitalPrintPriceViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})
print_price_by_machine = DigitalPrintPriceViewSet.as_view({
    "get": "by_machine"
})

material_price_list = MaterialPriceViewSet.as_view({
    "get": "list",
    "post": "create"
})
material_price_detail = MaterialPriceViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})
material_price_bulk = MaterialPriceViewSet.as_view({
    "post": "bulk_update_markup"
})

finishing_price_list = FinishingPriceViewSet.as_view({
    "get": "list",
    "post": "create"
})
finishing_price_detail = FinishingPriceViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})
finishing_by_category = FinishingPriceViewSet.as_view({
    "get": "by_category"
})

discount_list = VolumeDiscountViewSet.as_view({
    "get": "list",
    "post": "create"
})
discount_detail = VolumeDiscountViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})

# Simple Paper GSM Pricing
paper_gsm_list = PaperGSMPriceViewSet.as_view({
    "get": "list",
    "post": "create"
})
paper_gsm_detail = PaperGSMPriceViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})
paper_gsm_by_size = PaperGSMPriceViewSet.as_view({
    "get": "by_size"
})

urlpatterns = [
    # Digital Print Prices
    path("print/", print_price_list, name="print-price-list"),
    path("print/<int:pk>/", print_price_detail, name="print-price-detail"),
    path("print/by-machine/", print_price_by_machine, name="print-price-by-machine"),
    
    # Material Prices
    path("materials/", material_price_list, name="material-price-list"),
    path("materials/<int:pk>/", material_price_detail, name="material-price-detail"),
    path("materials/bulk-markup/", material_price_bulk, name="material-price-bulk"),
    
    # Finishing Prices
    path("finishing/", finishing_price_list, name="finishing-price-list"),
    path("finishing/<int:pk>/", finishing_price_detail, name="finishing-price-detail"),
    path("finishing/by-category/", finishing_by_category, name="finishing-by-category"),
    
    # Volume Discounts
    path("discounts/", discount_list, name="discount-list"),
    path("discounts/<int:pk>/", discount_detail, name="discount-detail"),
    
    # Composite Views (Complex)
    path("rate-card/", RateCardView.as_view(), name="rate-card"),
    path("calculate/", CostCalculatorView.as_view(), name="cost-calculator"),
    path("compare/", PriceComparisonView.as_view(), name="price-comparison"),
    
    # Simple/Customer-Friendly Pricing (NEW)
    # Paper GSM Prices - CRUD
    path("paper-gsm/", paper_gsm_list, name="paper-gsm-list"),
    path("paper-gsm/<int:pk>/", paper_gsm_detail, name="paper-gsm-detail"),
    path("paper-gsm/by-size/", paper_gsm_by_size, name="paper-gsm-by-size"),
    
    # Simple Rate Card (Public - for customers)
    path("simple-rate-card/", SimpleRateCardView.as_view(), name="simple-rate-card"),
    
    # Simple Calculator (Public - for customers)
    path("simple-calculate/", SimplePriceCalculatorView.as_view(), name="simple-calculator"),
]