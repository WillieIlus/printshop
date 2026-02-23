# pricing/admin.py
"""
Simple, layman-friendly admin for pricing.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    PrintingPrice,
    MaterialPrice,
    FinishingService,
    VolumeDiscount,
    DefaultPrintingPriceTemplate,
    DefaultPaperPriceTemplate,
    DefaultMaterialPriceTemplate,
    DefaultFinishingServiceTemplate,
)


@admin.register(PrintingPrice)
class PrintingPriceAdmin(admin.ModelAdmin):
    """Printing prices per side."""
    
    list_display = [
        "shop",
        "machine",
        "sheet_size",
        "color_mode",
        "selling_price_per_side",
        "selling_price_duplex_per_sheet",
        "buying_price_per_side",
        "profit_display",
        "is_active",
    ]
    list_filter = ["shop", "machine", "sheet_size", "color_mode", "is_active"]
    list_editable = ["selling_price_per_side", "selling_price_duplex_per_sheet", "buying_price_per_side", "is_active"]
    search_fields = ["shop__name", "machine__name"]
    ordering = ["shop", "sheet_size", "color_mode"]
    
    fieldsets = (
        ("Basic Info", {
            "fields": ("shop", "machine", "sheet_size", "color_mode")
        }),
        ("Pricing (per side)", {
            "fields": ("selling_price_per_side", "selling_price_duplex_per_sheet", "buying_price_per_side"),
            "description": "Set the price per printed side. Duplex override: optional price for both sides per sheet (e.g. 10 bob duplex vs 7×2 per side)."
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
    )
    
    def selling_price_display(self, obj):
        return format_html("<strong>KES {}</strong>", obj.selling_price_per_side)
    selling_price_display.short_description = "Sell Price"
    
    def buying_price_display(self, obj):
        if obj.buying_price_per_side:
            return f"KES {obj.buying_price_per_side}"
        return "-"
    buying_price_display.short_description = "Buy Price"
    
    def profit_display(self, obj):
        profit = obj.profit_per_side
        if profit > 0:
            return format_html('<span style="color: green;">KES {}</span>', profit)
        return "-"
    profit_display.short_description = "Profit"


@admin.register(MaterialPrice)
class MaterialPriceAdmin(admin.ModelAdmin):
    """Large-format materials (banner, vinyl, reflective) priced per SQM or sheet."""
    
    list_display = [
        "shop",
        "material_type",
        "unit",
        "selling_price",
        "buying_price",
        "is_active",
    ]
    list_filter = ["shop", "material_type", "unit", "is_active"]
    list_editable = ["selling_price", "buying_price", "is_active"]
    search_fields = ["shop__name"]
    ordering = ["shop", "material_type", "unit"]
    
    fieldsets = (
        ("Material", {
            "fields": ("shop", "material_type", "unit")
        }),
        ("Pricing", {
            "fields": ("selling_price", "buying_price"),
            "description": "Selling price per unit (e.g. per SQM for large format)"
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
    )
    
    def buying_price_display(self, obj):
        if obj.buying_price:
            return f"KES {obj.buying_price}"
        return "-"
    buying_price_display.short_description = "Buy"


@admin.register(FinishingService)
class FinishingServiceAdmin(admin.ModelAdmin):
    """Finishing services like lamination, binding, etc."""
    
    list_display = [
        "shop",
        "name",
        "category",
        "charge_by",
        "selling_price",
        "buying_price_display",
        "profit_display",
        "is_default",
        "is_active"
    ]
    list_filter = ["shop", "category", "charge_by", "is_active", "is_default"]
    list_editable = ["selling_price", "is_default", "is_active"]
    search_fields = ["shop__name", "name"]
    ordering = ["shop", "category", "name"]
    
    fieldsets = (
        ("Service Details", {
            "fields": ("shop", "name", "category", "charge_by")
        }),
        ("Pricing", {
            "fields": ("buying_price", "selling_price"),
            "description": "Set buying (your cost) and selling (customer pays) prices"
        }),
        ("Options", {
            "fields": ("is_default", "is_active"),
            "description": "'Selected by default' will pre-select this option for customers"
        }),
    )
    
    def buying_price_display(self, obj):
        if obj.buying_price > 0:
            return f"KES {obj.buying_price}"
        return "-"
    buying_price_display.short_description = "Buy"
    
    def selling_price_display(self, obj):
        return format_html("<strong>KES {}</strong>", obj.selling_price)
    selling_price_display.short_description = "Sell"
    
    def profit_display(self, obj):
        profit = obj.profit
        if profit > 0:
            return format_html('<span style="color: green;">KES {}</span>', profit)
        return "-"
    profit_display.short_description = "Profit"


@admin.register(VolumeDiscount)
class VolumeDiscountAdmin(admin.ModelAdmin):
    """Optional volume discounts."""
    
    list_display = [
        "shop",
        "name",
        "min_quantity",
        "discount_percent",
        "is_active"
    ]
    list_filter = ["shop", "is_active"]
    list_editable = ["discount_percent", "is_active"]
    ordering = ["shop", "min_quantity"]


# =============================================================================
# DEFAULT TEMPLATES
# =============================================================================

@admin.register(DefaultPrintingPriceTemplate)
class DefaultPrintingPriceTemplateAdmin(admin.ModelAdmin):
    list_display = ["machine_category", "sheet_size", "color_mode", "selling_price_per_side", "selling_price_duplex_per_sheet"]
    list_filter = ["machine_category", "sheet_size", "color_mode"]
    search_fields = ["machine_category"]
    ordering = ["machine_category", "sheet_size", "color_mode"]


@admin.register(DefaultPaperPriceTemplate)
class DefaultPaperPriceTemplateAdmin(admin.ModelAdmin):
    list_display = ["sheet_size", "paper_type", "gsm", "selling_price", "buying_price"]
    list_filter = ["sheet_size", "paper_type"]
    search_fields = ["sheet_size", "paper_type"]
    ordering = ["sheet_size", "gsm", "paper_type"]


@admin.register(DefaultMaterialPriceTemplate)
class DefaultMaterialPriceTemplateAdmin(admin.ModelAdmin):
    list_display = ["material_type", "unit", "selling_price", "buying_price"]
    list_filter = ["material_type", "unit"]
    search_fields = ["material_type"]
    ordering = ["material_type", "unit"]


@admin.register(DefaultFinishingServiceTemplate)
class DefaultFinishingServiceTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "unit_type", "selling_price", "buying_price"]
    list_filter = ["unit_type"]
    search_fields = ["name"]
    ordering = ["name"]
