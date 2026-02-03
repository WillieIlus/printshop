# quotes/admin.py

from decimal import Decimal
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
        (_("Part Definition"), {
            "fields": ("name", ("final_width", "final_height"))
        }),
        (_("Production Specs"), {
            "fields": ("material", "preferred_stock", "machine", "print_sides")
        }),
        (_("Calculated Results"), {
            "fields": ("items_per_sheet", "total_sheets_required", "part_cost"),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = ["items_per_sheet", "total_sheets_required", "part_cost"]
    autocomplete_fields = ["material", "machine", "preferred_stock"]


class QuoteItemFinishingInline(admin.TabularInline):
    model = QuoteItemFinishing
    extra = 1
    fields = ["finishing_price", "calculated_cost"]
    readonly_fields = ["calculated_cost"]
    autocomplete_fields = ["finishing_price"]


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
    list_display = ["name", "shop_name", "description_short", "created_at"]
    list_filter = ["shop"]
    search_fields = ["name", "shop__name"]
    ordering = ["shop", "name"]

    fieldsets = (
        (None, {
            "fields": ("shop", "name", "description")
        }),
        (_("Defaults"), {
            "fields": ("defaults",),
        }),
    )

    @admin.display(description="Shop", ordering="shop__name")
    def shop_name(self, obj):
        return obj.shop.name

    @admin.display(description="Description")
    def description_short(self, obj):
        return (obj.description[:50] + "...") if obj.description else "—"


# =============================================================================
# Quote Admin
# =============================================================================

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "user_email",
        "shop_name",
        "status_badge",
        "item_count",
        "net_total_display",
        "grand_total_display",
        "created_at",
    ]
    list_filter = ["status", "shop", "created_at"]
    search_fields = ["reference", "user__email", "shop__name"]
    ordering = ["-created_at"]
    list_per_page = 25
    
    readonly_fields = [
        "reference",
        "net_total",
        "tax_amount",
        "grand_total",
        "created_at",
        "updated_at",
        "calculation_breakdown",
    ]

    inlines = [QuoteItemInline]

    fieldsets = (
        (None, {
            "fields": ("shop", "user", "reference", "status")
        }),
        (_("Financials"), {
            "fields": (("net_total", "tax_amount", "grand_total"),),
        }),
        (_("Breakdown"), {
            "fields": ("calculation_breakdown",),
            "classes": ("collapse",),
        }),
        (_("Timestamps"), {
            "fields": (("created_at", "updated_at"),),
            "classes": ("collapse",),
        }),
    )

    actions = ["recalculate_quotes", "mark_as_sent", "mark_as_accepted"]

    @admin.display(description="User", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Shop", ordering="shop__name")
    def shop_name(self, obj):
        return obj.shop.name

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {"DRAFT": "#6c757d", "SENT": "#17a2b8", "ACCEPTED": "#28a745", "REJECTED": "#dc3545"}
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.items.count()

    @admin.display(description="Net")
    def net_total_display(self, obj):
        # Plain string formatting, no HTML injection
        return f"{float(obj.net_total or 0):,.2f}"

    @admin.display(description="Grand Total")
    def grand_total_display(self, obj):
        # Plain string formatting
        return f"{float(obj.grand_total or 0):,.2f}"

    @admin.display(description="Calculation Breakdown")
    def calculation_breakdown(self, obj):
        html = ['<table style="width:100%; border-collapse: collapse;">']
        html.append('<tr style="background:#f8f9fa;"><th style="padding:8px; border:1px solid #ddd;">Item</th><th style="padding:8px; border:1px solid #ddd;">Total</th></tr>')
        
        for item in obj.items.all():
            html.append(f'<tr><td style="padding:8px; border:1px solid #ddd;">{item.name} (Qty: {item.quantity})</td>')
            html.append(f'<td style="padding:8px; border:1px solid #ddd; text-align:right;">{item.calculated_price:,.2f}</td></tr>')
        
        html.append('</table>')
        return mark_safe("".join(html))

    def save_model(self, request, obj, form, change):
        if not obj.reference:
            count = Quote.objects.filter(shop=obj.shop).count() + 1
            obj.reference = f"Q-{obj.shop.slug.upper()[:3]}-{count:05d}"
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        quote = form.instance
        try:
            QuoteCalculator().calculate_quote_total(quote)
            messages.success(request, f"Calculated. Grand Total: {quote.grand_total:,.2f}")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    @admin.action(description="Recalculate Selected")
    def recalculate_quotes(self, request, queryset):
        calc = QuoteCalculator()
        for quote in queryset:
            try:
                calc.calculate_quote_total(quote)
            except Exception:
                pass
        messages.success(request, "Recalculation complete.")

    @admin.action(description="Mark as Sent")
    def mark_as_sent(self, request, queryset):
        queryset.update(status=Quote.Status.SENT)

    @admin.action(description="Mark as Accepted")
    def mark_as_accepted(self, request, queryset):
        queryset.update(status=Quote.Status.ACCEPTED)


# =============================================================================
# QuoteItem Admin (FIXED)
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
        (_("Total"), {
            "fields": ("calculated_price",)
        }),
    )

    @admin.display(description="Quote")
    def quote_link(self, obj):
        url = reverse("admin:quotes_quote_change", args=[obj.quote.id])
        label = obj.quote.reference or f"Quote #{obj.quote.id}"
        return format_html('<a href="{}">{}</a>', url, label)

    @admin.display(description="Price")
    def calculated_price_display(self, obj):
        # FIXED: Just return string, no format_html wrapper
        return f"{float(obj.calculated_price or 0):,.2f}"

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
        "item_name",
        "dimensions",
        "material_name",
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
        (_("Size"), {
            "fields": (("final_width", "final_height"),)
        }),
        (_("Specs"), {
            "fields": ("material", "preferred_stock", "machine", "print_sides")
        }),
        (_("Results"), {
            "fields": ("items_per_sheet", "total_sheets_required", "part_cost"),
        }),
    )

    @admin.display(description="Item")
    def item_name(self, obj):
        return obj.item.name

    @admin.display(description="Size")
    def dimensions(self, obj):
        return f"{obj.final_width} × {obj.final_height} mm"

    @admin.display(description="Material")
    def material_name(self, obj):
        return obj.material.name

    @admin.display(description="Cost")
    def cost_display(self, obj):
        # FIXED: Plain string
        return f"{float(obj.part_cost or 0):,.2f}"


# =============================================================================
# QuoteItemFinishing Admin
# =============================================================================

@admin.register(QuoteItemFinishing)
class QuoteItemFinishingAdmin(admin.ModelAdmin):
    list_display = [
        "service_name",
        "item_name",
        "cost_display",
    ]
    list_filter = ["finishing_price__category"]
    search_fields = ["finishing_price__process_name", "item__name"]

    readonly_fields = ["calculated_cost"]

    @admin.display(description="Service")
    def service_name(self, obj):
        return obj.finishing_price.process_name

    @admin.display(description="Item")
    def item_name(self, obj):
        return obj.item.name

    @admin.display(description="Cost")
    def cost_display(self, obj):
        # FIXED: Plain string
        return f"{float(obj.calculated_cost or 0):,.2f}"