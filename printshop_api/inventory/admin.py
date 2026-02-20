# inventory/admin.py
"""
Simple admin for inventory management.
"""

from django.contrib import admin
from django.utils.html import format_html

from pricing.models import PrintingPrice

from .models import Machine, PaperStock


class PrintingPriceInline(admin.TabularInline):
    """Inline for printing prices within Machine admin."""
    model = PrintingPrice
    extra = 0
    fields = ["sheet_size", "color_mode", "selling_price_per_side", "selling_price_duplex_per_sheet", "is_active"]
    ordering = ["sheet_size", "color_mode"]


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    """Manage printing machines."""
    
    list_display = [
        "shop",
        "name",
        "machine_type",
        "max_size_display",
        "is_active"
    ]
    list_filter = ["shop", "machine_type", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["name", "shop__name"]
    ordering = ["shop", "name"]
    
    fieldsets = (
        ("Basic Info", {
            "fields": ("shop", "name", "machine_type")
        }),
        ("Paper Size Limits (Optional)", {
            "fields": ("max_paper_width", "max_paper_height"),
            "classes": ("collapse",),
            "description": "Maximum paper size this machine can handle"
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
    )
    inlines = [PrintingPriceInline]

    def max_size_display(self, obj):
        if obj.max_paper_width and obj.max_paper_height:
            return f"{obj.max_paper_width} × {obj.max_paper_height} mm"
        return "-"
    max_size_display.short_description = "Max Size"


@admin.register(PaperStock)
class PaperStockAdmin(admin.ModelAdmin):
    """Manage paper stock/inventory."""
    
    list_display = [
        "shop",
        "sheet_size",
        "gsm",
        "paper_type",
        "quantity_in_stock",
        "reorder_status",
        "buying_price_display",
        "is_active"
    ]
    list_filter = ["shop", "sheet_size", "paper_type", "gsm", "is_active"]
    list_editable = ["quantity_in_stock", "is_active"]
    search_fields = ["shop__name"]
    ordering = ["shop", "sheet_size", "gsm"]
    
    fieldsets = (
        ("Paper Details", {
            "fields": ("shop", "sheet_size", "gsm", "paper_type")
        }),
        ("Dimensions", {
            "fields": ("width_mm", "height_mm"),
            "description": "Auto-filled based on paper size, or enter custom dimensions"
        }),
        ("Stock Levels", {
            "fields": ("quantity_in_stock", "reorder_level"),
            "description": "Track how much paper you have"
        }),
        ("Cost (Optional)", {
            "fields": ("buying_price_per_sheet",),
            "classes": ("collapse",),
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
    )
    
    def stock_display(self, obj):
        return f"{obj.quantity_in_stock} sheets"
    stock_display.short_description = "In Stock"
    stock_display.admin_order_field = "quantity_in_stock"
    
    def reorder_status(self, obj):
        if obj.needs_reorder:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ Low Stock</span>'
            )
        return format_html('<span style="color: green;">✓ OK</span>')
    reorder_status.short_description = "Status"
    
    def buying_price_display(self, obj):
        if obj.buying_price_per_sheet:
            return f"KES {obj.buying_price_per_sheet}"
        return "-"
    buying_price_display.short_description = "Cost/Sheet"
