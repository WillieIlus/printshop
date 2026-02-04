# pricing/admin.py

from decimal import Decimal
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from common.admin import SuperuserOrTestimonialAddMixin
from .models import (
    DigitalPrintPrice,
    FinishingOption,
    FinishingPrice,
    MaterialPrice,
    PaperGSMPrice,
    PricingEngine,
    PricingTier,
    PricingVariable,
    RawMaterial,
    VolumeDiscount,
)


# =============================================================================
# Inlines
# =============================================================================

class PricingTierInline(admin.TabularInline):
    """Inline for managing bulk pricing tiers within FinishingPrice."""
    model = PricingTier
    extra = 1
    fields = ["min_quantity", "max_quantity", "price_per_unit"]
    ordering = ["min_quantity"]


# =============================================================================
# Digital Print Price Admin
# =============================================================================

@admin.register(DigitalPrintPrice)
class DigitalPrintPriceAdmin(admin.ModelAdmin):
    list_display = [
        "machine_name",
        "shop_name",
        "sheet_size",
        "color_mode",
        "click_rate_display",
        "duplex_rate_display",
        "effective_duplex_display",
        "min_qty",
        "is_active",
    ]
    list_filter = ["shop", "machine", "sheet_size", "color_mode", "is_active"]
    search_fields = ["machine__name", "shop__name"]
    list_select_related = ["machine", "shop"]
    ordering = ["shop", "machine__name", "sheet_size"]
    list_per_page = 50
    
    fieldsets = (
        (None, {
            "fields": ("shop", "machine")
        }),
        (_("Configuration"), {
            "fields": ("sheet_size", "color_mode")
        }),
        (_("Pricing"), {
            "fields": ("click_rate", "duplex_rate", "minimum_order_quantity"),
            "description": "Duplex Rate is optional. If left blank, it defaults to 2× Click Rate."
        }),
        (_("Status"), {
            "fields": ("is_active",)
        }),
    )
    
    @admin.display(description="Machine", ordering="machine__name")
    def machine_name(self, obj):
        return obj.machine.name
    
    @admin.display(description="Shop", ordering="shop__name")
    def shop_name(self, obj):
        return obj.shop.name
    
    @admin.display(description="Side 1")
    def click_rate_display(self, obj):
        return format_html("<strong>{}</strong>", obj.click_rate)
    
    @admin.display(description="Side 2 (Set)")
    def duplex_rate_display(self, obj):
        if obj.duplex_rate:
            return obj.duplex_rate
        return format_html('<span style="color: #999;">—</span>')
    
    @admin.display(description="Effective Duplex")
    def effective_duplex_display(self, obj):
        return format_html("<strong>{}</strong>", obj.effective_duplex_rate)
    
    @admin.display(description="Min Qty")
    def min_qty(self, obj):
        return obj.minimum_order_quantity


# =============================================================================
# Material Price Admin
# =============================================================================

@admin.register(MaterialPrice)
class MaterialPriceAdmin(admin.ModelAdmin):
    list_display = [
        "material_name",
        "shop_name",
        "pricing_method",
        "cost_price",
        "selling_price",
        "profit_display",
        "margin_display",
        "is_active",
    ]
    list_filter = ["shop", "pricing_method", "is_active", "material__type"]
    search_fields = ["material__name", "shop__name"]
    list_select_related = ["material", "shop"]
    ordering = ["shop", "material__name"]
    list_per_page = 50
    
    fieldsets = (
        (None, {
            "fields": ("shop", "material")
        }),
        (_("Pricing Method"), {
            "fields": ("pricing_method",)
        }),
        (_("Price Configuration"), {
            "fields": ("selling_price_per_unit", "markup_percentage", "margin_percentage"),
            "description": "Fill in the relevant field based on pricing method."
        }),
        (_("Constraints"), {
            "fields": ("minimum_order_value",)
        }),
        (_("Status"), {
            "fields": ("is_active",)
        }),
    )
    
    @admin.display(description="Material", ordering="material__name")
    def material_name(self, obj):
        return obj.material.name
    
    @admin.display(description="Shop", ordering="shop__name")
    def shop_name(self, obj):
        return obj.shop.name
    
    @admin.display(description="Cost")
    def cost_price(self, obj):
        return obj.material.cost_per_unit
    
    @admin.display(description="Selling Price")
    def selling_price(self, obj):
        price = obj.calculated_selling_price.quantize(Decimal("0.01"))
        return format_html("<strong>{}</strong>", price)

        
    @admin.display(description="Profit/Unit")
    def profit_display(self, obj):
        profit = obj.profit_per_unit.quantize(Decimal("0.01"))
        color = "green" if profit > 0 else "red"
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            profit
        )

    
    @admin.display(description="Margin %")
    def margin_display(self, obj):
        margin = obj.effective_margin_percentage.quantize(Decimal("0.1"))
        return f"{margin}%"



# =============================================================================
# Paper GSM Price Admin (Customer-Friendly Pricing)
# =============================================================================

@admin.register(PaperGSMPrice)
class PaperGSMPriceAdmin(admin.ModelAdmin):
    """
    Admin for simple, transparent paper pricing by GSM.
    Allows shop owners to set prices customers can easily understand.
    
    Example rate card:
    - A3 130gsm Gloss: KES 10
    - A3 150gsm Gloss: KES 15
    - A3 200gsm Gloss: KES 20
    - A3 300gsm Gloss: KES 30
    """
    list_display = [
        "sheet_size",
        "gsm",
        "paper_type",
        "price_display",
        "cost_display",
        "profit_display",
        "margin_display",
        "shop_name",
        "is_active",
    ]
    list_filter = ["shop", "sheet_size", "paper_type", "is_active"]
    search_fields = ["shop__name", "paper_type"]
    list_select_related = ["shop"]
    ordering = ["shop", "sheet_size", "gsm"]
    list_per_page = 50
    list_editable = ["price_per_sheet", "is_active"] if False else []  # Set to True to enable inline editing
    
    fieldsets = (
        (None, {
            "fields": ("shop",),
        }),
        (_("Paper Details"), {
            "fields": ("sheet_size", "gsm", "paper_type"),
            "description": "Select the paper size and weight (GSM). Common GSM values: 80 (copy paper), 130, 150, 170, 200, 250, 300, 350."
        }),
        (_("Pricing"), {
            "fields": ("price_per_sheet", "cost_per_sheet"),
            "description": "Set the customer-facing price. Cost is optional (for your profit tracking)."
        }),
        (_("Status"), {
            "fields": ("is_active",)
        }),
    )
    
    @admin.display(description="Shop", ordering="shop__name")
    def shop_name(self, obj):
        return obj.shop.name
    
    @admin.display(description="Price/Sheet")
    def price_display(self, obj):
        return format_html("<strong>KES {}</strong>", obj.price_per_sheet)
    
    @admin.display(description="Cost/Sheet")
    def cost_display(self, obj):
        if obj.cost_per_sheet:
            return f"KES {obj.cost_per_sheet}"
        return format_html('<span style="color: #999;">—</span>')
    
    @admin.display(description="Profit/Sheet")
    def profit_display(self, obj):
        profit = obj.profit_per_sheet
        if profit > 0:
            return format_html('<span style="color: green;">KES {}</span>', profit)
        elif profit < 0:
            return format_html('<span style="color: red;">KES {}</span>', profit)
        return format_html('<span style="color: #999;">—</span>')
    
    @admin.display(description="Margin")
    def margin_display(self, obj):
        margin = obj.margin_percentage
        if margin > 0:
            return format_html('<span style="color: green;">{:.1f}%</span>', margin)
        return format_html('<span style="color: #999;">—</span>')

    actions = ["duplicate_for_other_sizes"]
    
    @admin.action(description="Duplicate selected prices for other sheet sizes")
    def duplicate_for_other_sizes(self, request, queryset):
        """Quickly set up pricing for multiple sheet sizes."""
        from django.contrib import messages
        
        created_count = 0
        for price in queryset:
            for size_code, size_label in PaperGSMPrice.SheetSize.choices:
                if size_code != price.sheet_size:
                    _, created = PaperGSMPrice.objects.get_or_create(
                        shop=price.shop,
                        sheet_size=size_code,
                        gsm=price.gsm,
                        paper_type=price.paper_type,
                        defaults={
                            "price_per_sheet": price.price_per_sheet,
                            "cost_per_sheet": price.cost_per_sheet,
                            "is_active": price.is_active,
                        }
                    )
                    if created:
                        created_count += 1
        
        messages.success(request, f"Created {created_count} new paper price entries.")


# =============================================================================
# Finishing Price Admin (with Tiers)
# =============================================================================

@admin.register(FinishingPrice)
class FinishingPriceAdmin(admin.ModelAdmin):
    list_display = [
        "process_name",
        "shop_name",
        "category",
        "price_display",
        "unit",
        "mandatory_display",
        "setup_fee",
        "tier_count",
        "is_active",
    ]
    list_filter = ["shop", "category", "unit", "is_mandatory", "is_default_selected", "is_active"]
    search_fields = ["process_name", "shop__name", "description"]
    list_select_related = ["shop"]
    ordering = ["shop", "category", "process_name"]
    list_per_page = 50
    inlines = [PricingTierInline]
    
    fieldsets = (
        (None, {
            "fields": ("shop", "category", "process_name", "description")
        }),
        (_("Pricing Logic"), {
            "fields": ("unit", "price", "batch_size"),
            "description": "Batch Size only applies when Unit is 'Per Batch'."
        }),
        (_("Additional Charges"), {
            "fields": ("setup_fee", "minimum_order_quantity")
        }),
        (_("Mandatory/Optional"), {
            "fields": ("is_mandatory", "is_default_selected"),
            "description": "Mandatory finishing is always included. Default selected is pre-checked for optional finishing."
        }),
        (_("Status"), {
            "fields": ("is_active",)
        }),
    )
    
    @admin.display(description="Shop", ordering="shop__name")
    def shop_name(self, obj):
        return obj.shop.name
    
    @admin.display(description="Price")
    def price_display(self, obj):
        return format_html("<strong>{}</strong> / {}", obj.price, obj.get_unit_display())

    @admin.display(description="Type")
    def mandatory_display(self, obj):
        if obj.is_mandatory:
            return format_html('<span style="color: red; font-weight: bold;">Mandatory</span>')
        elif obj.is_default_selected:
            return format_html('<span style="color: green;">Default</span>')
        return format_html('<span style="color: #999;">Optional</span>')
    
    @admin.display(description="Batch")
    def batch_info(self, obj):
        if obj.unit == "PER_BATCH":
            return f"per {obj.batch_size}"
        return "—"
    
    @admin.display(description="Tiers")
    def tier_count(self, obj):
        count = obj.tiers.count()
        if count > 0:
            return format_html('<span style="color: green; font-weight: bold;">{} tier(s)</span>', count)
        return format_html('<span style="color: #999;">None</span>')


# =============================================================================
# Pricing Tier Admin (Standalone Access)
# =============================================================================

@admin.register(PricingTier)
class PricingTierAdmin(admin.ModelAdmin):
    list_display = [
        "finishing_service_name",
        "shop_name",
        "quantity_range",
        "price_per_unit",
    ]
    list_filter = ["finishing_service__shop", "finishing_service__category"]
    search_fields = ["finishing_service__process_name", "finishing_service__shop__name"]
    list_select_related = ["finishing_service", "finishing_service__shop"]
    ordering = ["finishing_service__shop", "finishing_service", "min_quantity"]
    list_per_page = 50
    
    fieldsets = (
        (None, {
            "fields": ("finishing_service",)
        }),
        (_("Quantity Range"), {
            "fields": ("min_quantity", "max_quantity"),
            "description": "Leave 'Max Quantity' blank for unlimited (e.g., 100+)."
        }),
        (_("Pricing"), {
            "fields": ("price_per_unit",)
        }),
    )
    
    @admin.display(description="Service", ordering="finishing_service__process_name")
    def finishing_service_name(self, obj):
        return obj.finishing_service.process_name
    
    @admin.display(description="Shop")
    def shop_name(self, obj):
        return obj.finishing_service.shop.name
    
    @admin.display(description="Quantity Range")
    def quantity_range(self, obj):
        if obj.max_quantity:
            return f"{obj.min_quantity} – {obj.max_quantity}"
        return f"{obj.min_quantity}+"


# =============================================================================
# Volume Discount Admin
# =============================================================================

@admin.register(VolumeDiscount)
class VolumeDiscountAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "shop_name",
        "quantity_range",
        "discount_display",
        "applies_to",
        "is_active",
    ]
    list_filter = [
        "shop", 
        "discount_type", 
        "is_active",
        "applies_to_print",
        "applies_to_material",
        "applies_to_finishing",
    ]
    search_fields = ["name", "shop__name"]
    list_select_related = ["shop"]
    ordering = ["shop", "minimum_quantity"]
    list_per_page = 50
    
    fieldsets = (
        (None, {
            "fields": ("shop", "name")
        }),
        (_("Quantity Range"), {
            "fields": ("minimum_quantity", "maximum_quantity")
        }),
        (_("Discount Configuration"), {
            "fields": ("discount_type", "discount_value")
        }),
        (_("Applicability"), {
            "fields": ("applies_to_print", "applies_to_material", "applies_to_finishing")
        }),
        (_("Status"), {
            "fields": ("is_active",)
        }),
    )
    
    @admin.display(description="Shop", ordering="shop__name")
    def shop_name(self, obj):
        return obj.shop.name
    
    @admin.display(description="Quantity Range")
    def quantity_range(self, obj):
        if obj.maximum_quantity:
            return f"{obj.minimum_quantity} – {obj.maximum_quantity}"
        return f"{obj.minimum_quantity}+"
    
    @admin.display(description="Discount")
    def discount_display(self, obj):
        if obj.discount_type == "PERCENTAGE":
            return format_html('<span style="color: green;">{}% off</span>', obj.discount_value)
        elif obj.discount_type == "AMOUNT_OFF":
            return format_html('<span style="color: green;">{} off</span>', obj.discount_value)
        return f"Fixed: {obj.discount_value}"
    
    @admin.display(description="Applies To")
    def applies_to(self, obj):
        parts = []
        if obj.applies_to_print:
            parts.append("Print")
        if obj.applies_to_material:
            parts.append("Material")
        if obj.applies_to_finishing:
            parts.append("Finishing")
        return ", ".join(parts) or "None"


# =============================================================================
# Pricing engine (centralized rates + instant quote)
# =============================================================================


@admin.register(PricingVariable)
class PricingVariableAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = ["name", "key", "value", "last_updated"]
    search_fields = ["name", "key"]
    ordering = ["key"]


@admin.register(RawMaterial)
class RawMaterialAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = ["material_type", "cost_per_unit", "unit_measure", "created_at"]
    list_filter = ["unit_measure"]
    search_fields = ["material_type"]
    ordering = ["material_type"]


@admin.register(FinishingOption)
class FinishingOptionAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = ["process_name", "setup_fee", "unit_cost", "created_at"]
    search_fields = ["process_name"]
    ordering = ["process_name"]


@admin.register(PricingEngine)
class PricingEngineAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = ["product_name", "material", "finish_count", "created_at"]
    list_filter = ["material"]
    search_fields = ["product_name", "material__material_type"]
    list_select_related = ["material"]
    filter_horizontal = ["finishes"]
    autocomplete_fields = ["material"]

    @admin.display(description=_("finishes"))
    def finish_count(self, obj):
        return obj.finishes.count()