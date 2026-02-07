from django.contrib import admin
from django.http import HttpRequest

from .models import Testimonial


class SuperuserOrTestimonialAddMixin:
    """
    Restrict add permission: only superusers can add any model.
    Non-superusers can only add Testimonial.
    Use this mixin on all ModelAdmins (including Testimonial's) so the rule is consistent.
    """

    def has_add_permission(self, request: HttpRequest) -> bool:
        base = super().has_add_permission(request)
        if request.user.is_superuser:
            return base
        if self.model == Testimonial:
            return base
        return False


@admin.register(Testimonial)
class TestimonialAdmin(SuperuserOrTestimonialAddMixin, admin.ModelAdmin):
    list_display = ["author_name", "author_role", "is_approved", "order", "created_at"]
    list_filter = ["is_approved"]
    search_fields = ["author_name", "author_role", "quote"]
    list_editable = ["is_approved", "order"]
    ordering = ["order", "created_at"]
    fieldsets = (
        (None, {"fields": ("author_name", "author_role", "quote")}),
        ("Display", {"fields": ("is_approved", "order")}),
    )
