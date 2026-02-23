# inventory/admin.py
"""
Admin for inventory: Machine (with PrintingPrice inline), Paper.
"""

from django.contrib import admin
from django.utils.html import format_html

from pricing.models import PrintingPrice

from .models import Machine, Paper


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


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    """Manage paper (unified: buy/sell + optional stock)."""
    
    list_display = [
        "shop",
        "sheet_size",
        "gsm",
        "paper_type",
        "buying_price",
        "selling_price",
        "quantity_in_stock",
        "reorder_status",
        "is_active"
    ]
    list_filter = ["shop", "sheet_size", "paper_type", "gsm", "is_active"]
    list_editable = ["buying_price", "selling_price", "is_active"]
    search_fields = ["shop__name", "sheet_size", "paper_type"]
    ordering = ["shop", "sheet_size", "gsm"]
    
    fieldsets = (
        ("Paper Details", {
            "fields": ("shop", "sheet_size", "gsm", "paper_type")
        }),
        ("Dimensions", {
            "fields": ("width_mm", "height_mm"),
            "description": "Auto-filled based on paper size"
        }),
        ("Pricing", {
            "fields": ("buying_price", "selling_price"),
            "description": "What you pay and what customer pays per sheet"
        }),
        ("Stock (Optional)", {
            "fields": ("quantity_in_stock", "reorder_level"),
            "classes": ("collapse",),
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
    )
    
    def reorder_status(self, obj):
        if obj.needs_reorder:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ Low Stock</span>'
            )
        return format_html('<span style="color: green;">✓ OK</span>')
    reorder_status.short_description = "Status"
