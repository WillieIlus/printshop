from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from common.admin import SuperuserOrTestimonialAddMixin
from .models import PrintTemplate, TemplateCategory, TemplateFinishing, TemplateOption


# =============================================================================
# Inlines
# =============================================================================

class TemplateFinishingInline(admin.TabularInline):
    """Inline for managing finishing options within a template."""
    model = TemplateFinishing
    extra = 1
    fields = ["name", "is_mandatory", "is_default", "price_adjustment", "display_order"]
    ordering = ["display_order", "name"]


class TemplateOptionInline(admin.TabularInline):
    """Inline for managing options within a template."""
    model = TemplateOption
    extra = 1
    fields = ["option_type", "label", "value", "price_modifier", "is_default", "display_order"]
    ordering = ["option_type", "display_order"]


# =============================================================================
# Category Admin
# =============================================================================

@admin.register(TemplateCategory)
class TemplateCategoryAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = ["display_order", "name", "slug", "shop", "template_count", "is_active", "created_at"]
    list_display_links = ["name"]
    list_filter = ["shop", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "slug"]
    list_editable = ["display_order", "is_active"]
    ordering = ["display_order", "name"]

    autocomplete_fields = ["shop"]
    fieldsets = (
        (None, {
            "fields": ("shop", "name", "slug", "description")
        }),
        (_("Display"), {
            "fields": ("icon_svg_path", "display_order", "is_active")
        }),
    )

    @admin.display(description=_("templates"))
    def template_count(self, obj):
        count = obj.print_templates.filter(is_active=True).count()
        return format_html('<strong>{}</strong>', count)


# =============================================================================
# Print Template Admin
# =============================================================================

@admin.register(PrintTemplate)
class PrintTemplateAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display_links = ["title"]
    list_display = [
        "shop",
        "title",
        "slug",
        "category",
        "min_quantity",
        "min_gsm",
        "max_gsm",
        "base_price",
        "dimensions_label",
        "weight_label",
        "badges_display",
        "is_active",
        "created_at",
    ]
    list_filter = ["shop", "category", "is_popular", "is_best_value", "is_new", "is_active"]
    search_fields = ["title", "slug", "category__name", "description"]
    list_select_related = ["category"]
    list_editable = ["min_quantity", "min_gsm", "max_gsm", "base_price", "is_active"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [TemplateFinishingInline, TemplateOptionInline]
    ordering = ["category", "title"]

    autocomplete_fields = ["shop", "category"]
    fieldsets = (
        (None, {
            "fields": ("shop", "title", "slug", "category", "description")
        }),
        (_("Pricing"), {
            "fields": ("base_price", "min_quantity", "min_gsm", "max_gsm"),
            "description": _("base_price is starting price for display"),
        }),
        (_("Specifications"), {
            "fields": ("final_width", "final_height", "default_gsm", "default_print_sides"),
            "description": "Product specifications for quote conversion"
        }),
        (_("Display"), {
            "fields": ("preview_image", "dimensions_label", "weight_label")
        }),
        (_("Badges"), {
            "fields": ("is_popular", "is_best_value", "is_new"),
            "classes": ("collapse",)
        }),
        (_("SEO"), {
            "fields": ("meta_description",),
            "classes": ("collapse",)
        }),
        (_("Status"), {
            "fields": ("is_active",)
        }),
    )

    @admin.display(description=_("starting price"))
    def base_price_display(self, obj):
        return format_html('<strong>{}</strong>', obj.get_starting_price_display())

    @admin.display(description=_("badges"))
    def badges_display(self, obj):
        badges = obj.get_gallery_badges()
        if badges:
            badge_html = " ".join([
                f'<span style="background: #007bff; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-right: 4px;">{b}</span>'
                for b in badges
            ])
            return format_html(badge_html)
        return format_html('<span style="color: #999;">—</span>')


# =============================================================================
# Template Finishing Admin (Standalone)
# =============================================================================

@admin.register(TemplateFinishing)
class TemplateFinishingAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "template",
        "mandatory_display",
        "price_adjustment",
        "display_order",
    ]
    list_filter = ["is_mandatory", "is_default", "template__category"]
    search_fields = ["name", "template__title"]
    list_select_related = ["template"]
    ordering = ["template", "display_order"]

    @admin.display(description=_("type"), boolean=False)
    def mandatory_display(self, obj):
        if obj.is_mandatory:
            return format_html('<span style="color: red; font-weight: bold;">Mandatory</span>')
        elif obj.is_default:
            return format_html('<span style="color: green;">Default</span>')
        return format_html('<span style="color: #999;">Optional</span>')


# =============================================================================
# Template Option Admin (Standalone)
# =============================================================================

@admin.register(TemplateOption)
class TemplateOptionAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = [
        "template",
        "option_type",
        "label",
        "value",
        "price_modifier",
        "is_default",
    ]
    list_filter = ["option_type", "is_default", "template__category"]
    search_fields = ["label", "template__title"]
    list_select_related = ["template"]
    ordering = ["template", "option_type", "display_order"]
