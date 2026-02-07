# quotes/admin.py
"""
Admin for quotes management.
"""

from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from .models import (
    ProductTemplate,
    Quote,
    QuoteItem,
    QuoteItemPart,
    QuoteItemFinishing,
)
from .services import QuoteCalculator


# =============================================================================
# Inlines
# =============================================================================

class QuoteItemPartInline(admin.StackedInline):
    model = QuoteItemPart
    extra = 1
    classes = ["collapse"]
    
    fieldsets = (
        ("Part Details", {
            "fields": ("name", ("final_width", "final_height"))
        }),
        ("Paper & Printing", {
            "fields": ("paper_stock", "paper_gsm", "machine", "print_sides")
        }),
        ("Calculated Results", {
            "fields": ("items_per_sheet", "total_sheets_required", "part_cost"),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = ["items_per_sheet", "total_sheets_required", "part_cost"]


class QuoteItemFinishingInline(admin.TabularInline):
    model = QuoteItemFinishing
    extra = 1
    fields = ["finishing_service", "calculated_cost"]
    readonly_fields = ["calculated_cost"]


class QuoteItemInline(admin.StackedInline):
    model = QuoteItem
    extra = 1
    show_change_link = True
    
    fieldsets = (
        (None, {
            "fields": ("name", "quantity", "calculated_price")
        }),
    )
    
    readonly_fields = ["calculated_price"]


# =============================================================================
# Product Template Admin
# =============================================================================

@admin.register(ProductTemplate)
class ProductTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "shop", "description_short", "is_active"]
    list_filter = ["shop", "is_active"]
    search_fields = ["name", "shop__name"]
    ordering = ["shop", "name"]
    list_editable = ["is_active"]

    fieldsets = (
        (None, {
            "fields": ("shop", "name", "description", "is_active")
        }),
        ("Default Settings (JSON)", {
            "fields": ("defaults",),
            "description": "Example: {\"width\": 85, \"height\": 55, \"gsm\": 300, \"sides\": 2}"
        }),
    )

    @admin.display(description="Description")
    def description_short(self, obj):
        return (obj.description[:50] + "...") if obj.description else "-"


# =============================================================================
# Quote Admin
# =============================================================================

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "user",
        "shop",
        "status_badge",
        "item_count",
        "grand_total_display",
        "created_at",
    ]
    list_filter = ["status", "shop", "created_at"]
    search_fields = ["reference", "user__email", "shop__name", "title"]
    ordering = ["-created_at"]
    list_per_page = 25
    
    readonly_fields = [
        "reference",
        "net_total",
        "tax_amount",
        "grand_total",
        "created_at",
        "updated_at",
    ]

    inlines = [QuoteItemInline]

    fieldsets = (
        ("Quote Info", {
            "fields": ("shop", "user", "reference", "title", "status")
        }),
        ("Notes", {
            "fields": ("customer_notes", "internal_notes"),
            "classes": ("collapse",),
        }),
        ("Pricing", {
            "fields": (
                ("net_total", "discount_amount"),
                ("tax_rate", "tax_amount"),
                "grand_total"
            ),
        }),
        ("Validity", {
            "fields": ("valid_until",),
            "classes": ("collapse",),
        }),
    )

    actions = ["recalculate_quotes", "mark_as_sent", "mark_as_accepted"]

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "DRAFT": "#6c757d", 
            "PENDING": "#ffc107",
            "SENT": "#17a2b8", 
            "ACCEPTED": "#28a745", 
            "REJECTED": "#dc3545",
            "EXPIRED": "#6c757d",
            "CONVERTED": "#007bff",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.items.count()

    @admin.display(description="Total")
    def grand_total_display(self, obj):
        return f"KES {obj.grand_total:,.2f}"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        quote = form.instance
        try:
            QuoteCalculator().calculate_quote_total(quote)
            messages.success(request, f"Quote calculated: KES {quote.grand_total:,.2f}")
        except Exception as e:
            messages.error(request, f"Calculation error: {str(e)}")

    @admin.action(description="Recalculate selected quotes")
    def recalculate_quotes(self, request, queryset):
        calc = QuoteCalculator()
        count = 0
        for quote in queryset:
            try:
                calc.calculate_quote_total(quote)
                count += 1
            except Exception:
                pass
        messages.success(request, f"Recalculated {count} quotes.")

    @admin.action(description="Mark as Sent")
    def mark_as_sent(self, request, queryset):
        queryset.update(status=Quote.Status.SENT)

    @admin.action(description="Mark as Accepted")
    def mark_as_accepted(self, request, queryset):
        queryset.update(status=Quote.Status.ACCEPTED)


# =============================================================================
# QuoteItem Admin
# =============================================================================

@admin.register(QuoteItem)
class QuoteItemAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "quantity",
        "quote_link",
        "calculated_price_display",
    ]
    list_filter = ["quote__shop", "quote__status"]
    search_fields = ["name", "quote__reference"]
    ordering = ["-quote__created_at"]
    
    readonly_fields = ["calculated_price"]
    inlines = [QuoteItemPartInline, QuoteItemFinishingInline]

    fieldsets = (
        (None, {
            "fields": ("quote", "name", "quantity")
        }),
        ("Calculated", {
            "fields": ("calculated_price",)
        }),
    )

    @admin.display(description="Quote")
    def quote_link(self, obj):
        url = reverse("admin:quotes_quote_change", args=[obj.quote.id])
        return format_html('<a href="{}">{}</a>', url, obj.quote.reference)

    @admin.display(description="Price")
    def calculated_price_display(self, obj):
        return f"KES {obj.calculated_price:,.2f}"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        try:
            QuoteCalculator().calculate_quote_total(form.instance.quote)
            messages.success(request, "Quote recalculated.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")


# =============================================================================
# QuoteItemPart Admin
# =============================================================================

@admin.register(QuoteItemPart)
class QuoteItemPartAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "item",
        "dimensions",
        "print_sides",
        "sheets_display",
        "cost_display",
    ]
    list_filter = ["print_sides", "item__quote__shop"]
    search_fields = ["name", "item__name"]
    ordering = ["-item__quote__created_at"]

    readonly_fields = ["items_per_sheet", "total_sheets_required", "part_cost"]

    fieldsets = (
        (None, {
            "fields": ("item", "name")
        }),
        ("Dimensions (mm)", {
            "fields": (("final_width", "final_height"),)
        }),
        ("Paper", {
            "fields": ("paper_stock", "paper_gsm"),
            "description": "Select paper from stock OR enter GSM directly"
        }),
        ("Printing", {
            "fields": ("machine", "print_sides")
        }),
        ("Calculated", {
            "fields": ("items_per_sheet", "total_sheets_required", "part_cost"),
        }),
    )

    @admin.display(description="Size")
    def dimensions(self, obj):
        return f"{obj.final_width} × {obj.final_height} mm"

    @admin.display(description="Sheets")
    def sheets_display(self, obj):
        return f"{obj.total_sheets_required} ({obj.items_per_sheet}/sheet)"

    @admin.display(description="Cost")
    def cost_display(self, obj):
        return f"KES {obj.part_cost:,.2f}"


# =============================================================================
# QuoteItemFinishing Admin
# =============================================================================

@admin.register(QuoteItemFinishing)
class QuoteItemFinishingAdmin(admin.ModelAdmin):
    list_display = [
        "finishing_service",
        "item",
        "cost_display",
    ]
    list_filter = ["finishing_service__category"]
    search_fields = ["finishing_service__name", "item__name"]

    readonly_fields = ["calculated_cost"]

    @admin.display(description="Cost")
    def cost_display(self, obj):
        return f"KES {obj.calculated_cost:,.2f}"
