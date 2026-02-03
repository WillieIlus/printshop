from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from common.admin import SuperuserOrTestimonialAddMixin
from .models import PrintTemplate, TemplateCategory


@admin.register(TemplateCategory)
class TemplateCategoryAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = ["name", "slug", "template_count", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]

    @admin.display(description=_("templates"))
    def template_count(self, obj):
        return obj.print_templates.count()


@admin.register(PrintTemplate)
class PrintTemplateAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "base_price_display",
        "dimensions_label",
        "weight_label",
        "is_popular",
        "is_best_value",
        "created_at",
    ]
    list_filter = ["category", "is_popular", "is_best_value"]
    search_fields = ["title", "category__name"]
    list_select_related = ["category"]
    list_editable = ["is_popular", "is_best_value"]

    @admin.display(description=_("base price"))
    def base_price_display(self, obj):
        return obj.get_starting_price_display()
