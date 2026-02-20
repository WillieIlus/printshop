# shops/admin.py

"""
Django Admin configuration for the shops app.

Provides admin interfaces for:
- Shop management with inlines for members, hours, and social links
- ShopMember management
- OpeningHours management
- ShopSocialLink management
- ShopClaim workflow with approval actions
"""

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import OpeningHours, Shop, ShopClaim, ShopMember, ShopPaperCapability, ShopSocialLink


# =============================================================================
# Inline Admin Classes
# =============================================================================


class ShopMemberInline(admin.TabularInline):
    """Inline admin for shop members within Shop admin."""
    
    model = ShopMember
    extra = 0
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]
    fields = ["user", "role", "is_active", "created_at"]
    
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("user")


class OpeningHoursInline(admin.TabularInline):
    """Inline admin for opening hours within Shop admin."""
    
    model = OpeningHours
    extra = 0
    fields = ["weekday", "from_hour", "to_hour", "is_closed"]
    ordering = ["weekday", "from_hour"]


class ShopPaperCapabilityInline(admin.TabularInline):
    """Inline admin for paper capabilities within Shop admin."""

    model = ShopPaperCapability
    extra = 0
    fields = ["sheet_size", "min_gsm", "max_gsm"]
    ordering = ["sheet_size"]


class ShopSocialLinkInline(admin.TabularInline):
    """Inline admin for social links within Shop admin."""
    
    model = ShopSocialLink
    extra = 0
    fields = ["platform", "url", "username"]


class ShopClaimInline(admin.TabularInline):
    """Inline admin for claims within Shop admin (read-only)."""
    
    model = ShopClaim
    extra = 0
    readonly_fields = ["user", "business_name", "business_email", "status", "created_at"]
    fields = ["user", "business_name", "business_email", "status", "created_at"]
    can_delete = False
    show_change_link = True
    
    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


# =============================================================================
# Shop Admin
# =============================================================================


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Admin interface for Shop model."""
    
    list_display = [
        "name",
        "slug",
        "owner_email",
        "city",
        "state",
        "country",
        "is_verified_display",
        "is_active_display",
        "member_count",
        "created_at",
    ]
    list_filter = [
        "is_verified",
        "is_active",
        "country",
        "state",
        "created_at",
    ]
    search_fields = [
        "name",
        "slug",
        "business_email",
        "owner__email",
        "owner__first_name",
        "owner__last_name",
        "city",
        "address_line",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "member_count",
        "google_maps_link",
    ]
    autocomplete_fields = ["owner"]
    prepopulated_fields = {"slug": ("name",)}
    date_hierarchy = "created_at"
    list_per_page = 25
    list_select_related = ["owner"]
    ordering = ["-created_at"]
    save_on_top = True
    
    fieldsets = (
        (None, {
            "fields": ("name", "slug", "owner", "description"),
        }),
        (_("Contact Information"), {
            "fields": ("business_email", "phone_number"),
        }),
        (_("Location"), {
            "fields": (
                "address_line",
                ("city", "state"),
                ("zip_code", "country"),
            ),
        }),
        (_("GPS Coordinates"), {
            "fields": (
                ("latitude", "longitude"),
                "google_maps_link",
            ),
            "classes": ("collapse",),
        }),
        (_("Status"), {
            "fields": (
                ("is_verified", "is_active"),
            ),
        }),
        (_("Statistics"), {
            "fields": ("member_count",),
            "classes": ("collapse",),
        }),
        (_("Timestamps"), {
            "fields": (("created_at", "updated_at"),),
            "classes": ("collapse",),
        }),
    )
    
    inlines = [
        ShopMemberInline,
        OpeningHoursInline,
        ShopPaperCapabilityInline,
        ShopSocialLinkInline,
        ShopClaimInline,
    ]
    
    actions = [
        "verify_shops",
        "unverify_shops",
        "activate_shops",
        "deactivate_shops",
    ]
    
    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).annotate(
            _member_count=Count("members", distinct=True)
        ).select_related("owner")
    
    @admin.display(description=_("Owner Email"), ordering="owner__email")
    def owner_email(self, obj: Shop) -> str:
        return obj.owner.email
    
    @admin.display(description=_("Verified"), boolean=True, ordering="is_verified")
    def is_verified_display(self, obj: Shop) -> bool:
        return obj.is_verified
    
    @admin.display(description=_("Active"), boolean=True, ordering="is_active")
    def is_active_display(self, obj: Shop) -> bool:
        return obj.is_active
    
    @admin.display(description=_("Members"))
    def member_count(self, obj: Shop) -> int:
        if hasattr(obj, "_member_count"):
            return obj._member_count
        return obj.members.count()
    
    @admin.display(description=_("Google Maps"))
    def google_maps_link(self, obj: Shop) -> str:
        if obj.latitude and obj.longitude:
            url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">View on Google Maps</a>',
                url
            )
        return "-"
    
    @admin.action(description=_("Mark selected shops as verified"))
    def verify_shops(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(is_verified=True)
        self.message_user(
            request,
            _("%(count)d shop(s) marked as verified.") % {"count": updated}
        )
    
    @admin.action(description=_("Remove verification from selected shops"))
    def unverify_shops(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(is_verified=False)
        self.message_user(
            request,
            _("%(count)d shop(s) had verification removed.") % {"count": updated}
        )
    
    @admin.action(description=_("Activate selected shops"))
    def activate_shops(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            _("%(count)d shop(s) activated.") % {"count": updated}
        )
    
    @admin.action(description=_("Deactivate selected shops"))
    def deactivate_shops(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            _("%(count)d shop(s) deactivated.") % {"count": updated}
        )


# =============================================================================
# Shop Member Admin
# =============================================================================


@admin.register(ShopMember)
class ShopMemberAdmin(admin.ModelAdmin):
    """Admin interface for ShopMember model."""
    
    list_display = [
        "user_email",
        "user_name",
        "shop_name",
        "role",
        "is_active_display",
        "created_at",
    ]
    list_filter = [
        "role",
        "is_active",
        "shop",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "shop__name",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["shop", "user"]
    list_select_related = ["user", "shop"]
    ordering = ["-created_at"]
    list_per_page = 50
    
    fieldsets = (
        (None, {
            "fields": ("shop", "user", "role"),
        }),
        (_("Status"), {
            "fields": ("is_active",),
        }),
        (_("Timestamps"), {
            "fields": (("created_at", "updated_at"),),
            "classes": ("collapse",),
        }),
    )
    
    actions = ["activate_members", "deactivate_members"]
    
    @admin.display(description=_("User Email"), ordering="user__email")
    def user_email(self, obj: ShopMember) -> str:
        return obj.user.email
    
    @admin.display(description=_("User Name"))
    def user_name(self, obj: ShopMember) -> str:
        return obj.user.get_full_name() or "-"
    
    @admin.display(description=_("Shop"), ordering="shop__name")
    def shop_name(self, obj: ShopMember) -> str:
        return obj.shop.name
    
    @admin.display(description=_("Active"), boolean=True, ordering="is_active")
    def is_active_display(self, obj: ShopMember) -> bool:
        return obj.is_active
    
    @admin.action(description=_("Activate selected memberships"))
    def activate_members(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            _("%(count)d membership(s) activated.") % {"count": updated}
        )
    
    @admin.action(description=_("Deactivate selected memberships"))
    def deactivate_members(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            _("%(count)d membership(s) deactivated.") % {"count": updated}
        )


# =============================================================================
# Opening Hours Admin
# =============================================================================


@admin.register(OpeningHours)
class OpeningHoursAdmin(admin.ModelAdmin):
    """Admin interface for OpeningHours model."""
    
    list_display = [
        "shop_name",
        "weekday",
        "from_hour",
        "to_hour",
        "is_closed_display",
    ]
    list_filter = [
        "weekday",
        "is_closed",
        "shop",
    ]
    search_fields = [
        "shop__name",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["shop"]
    list_select_related = ["shop"]
    ordering = ["shop__name", "weekday", "from_hour"]
    list_per_page = 50
    
    fieldsets = (
        (None, {
            "fields": ("shop", "weekday"),
        }),
        (_("Hours"), {
            "fields": (("from_hour", "to_hour"), "is_closed"),
        }),
        (_("Timestamps"), {
            "fields": (("created_at", "updated_at"),),
            "classes": ("collapse",),
        }),
    )
    
    @admin.display(description=_("Shop"), ordering="shop__name")
    def shop_name(self, obj: OpeningHours) -> str:
        return obj.shop.name
    
    @admin.display(description=_("Closed"), boolean=True, ordering="is_closed")
    def is_closed_display(self, obj: OpeningHours) -> bool:
        return obj.is_closed


# =============================================================================
# Shop Social Link Admin
# =============================================================================


@admin.register(ShopSocialLink)
class ShopSocialLinkAdmin(admin.ModelAdmin):
    """Admin interface for ShopSocialLink model."""
    
    list_display = [
        "shop_name",
        "platform",
        "url_link",
        "username",
        "created_at",
    ]
    list_filter = [
        "platform",
        "shop",
        "created_at",
    ]
    search_fields = [
        "shop__name",
        "url",
        "username",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["shop"]
    list_select_related = ["shop"]
    ordering = ["shop__name", "platform"]
    list_per_page = 50
    
    fieldsets = (
        (None, {
            "fields": ("shop", "platform"),
        }),
        (_("Link Details"), {
            "fields": ("url", "username"),
        }),
        (_("Timestamps"), {
            "fields": (("created_at", "updated_at"),),
            "classes": ("collapse",),
        }),
    )
    
    @admin.display(description=_("Shop"), ordering="shop__name")
    def shop_name(self, obj: ShopSocialLink) -> str:
        return obj.shop.name
    
    @admin.display(description=_("URL"))
    def url_link(self, obj: ShopSocialLink) -> str:
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{}</a>',
            obj.url,
            obj.url[:50] + "..." if len(obj.url) > 50 else obj.url
        )


# =============================================================================
# Shop Claim Admin
# =============================================================================


@admin.register(ShopClaim)
class ShopClaimAdmin(admin.ModelAdmin):
    """Admin interface for ShopClaim model with approval workflow."""
    
    list_display = [
        "business_name",
        "user_email",
        "business_email",
        "shop_link",
        "status_badge",
        "created_at",
    ]
    list_filter = [
        "status",
        "created_at",
    ]
    search_fields = [
        "business_name",
        "business_email",
        "user__email",
        "user__first_name",
        "user__last_name",
        "shop__name",
    ]
    readonly_fields = [
        "user",
        "token",
        "created_at",
        "updated_at",
        "verification_link",
    ]
    autocomplete_fields = ["shop"]
    list_select_related = ["user", "shop"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    list_per_page = 25
    
    fieldsets = (
        (None, {
            "fields": ("user", "shop"),
        }),
        (_("Claim Details"), {
            "fields": ("business_name", "business_email"),
        }),
        (_("Status"), {
            "fields": ("status", "admin_notes"),
        }),
        (_("Verification"), {
            "fields": ("token", "verification_link"),
            "classes": ("collapse",),
        }),
        (_("Timestamps"), {
            "fields": (("created_at", "updated_at"),),
            "classes": ("collapse",),
        }),
    )
    
    actions = [
        "approve_claims",
        "reject_claims",
        "reset_to_pending",
    ]
    
    @admin.display(description=_("User Email"), ordering="user__email")
    def user_email(self, obj: ShopClaim) -> str:
        return obj.user.email
    
    @admin.display(description=_("Shop"))
    def shop_link(self, obj: ShopClaim) -> str:
        if obj.shop:
            return format_html(
                '<a href="/admin/shops/shop/{}/change/">{}</a>',
                obj.shop.pk,
                obj.shop.name
            )
        return format_html('<span style="color: #999;">New listing</span>')
    
    @admin.display(description=_("Status"))
    def status_badge(self, obj: ShopClaim) -> str:
        colors = {
            ShopClaim.Status.PENDING: "#f0ad4e",  # Orange/yellow
            ShopClaim.Status.VERIFIED: "#5cb85c",  # Green
            ShopClaim.Status.REJECTED: "#d9534f",  # Red
        }
        color = colors.get(obj.status, "#777")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    @admin.display(description=_("Verification Link"))
    def verification_link(self, obj: ShopClaim) -> str:
        from django.conf import settings
        base_url = getattr(settings, "SHOP_CLAIM_VERIFICATION_URL", "")
        if base_url:
            url = f"{base_url}?token={obj.token}"
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                url,
                url
            )
        return str(obj.token)
    
    @admin.action(description=_("Approve selected claims"))
    def approve_claims(self, request: HttpRequest, queryset: QuerySet) -> None:
        from django.db import transaction
        
        pending_claims = queryset.filter(status=ShopClaim.Status.PENDING)
        approved_count = 0
        
        for claim in pending_claims:
            with transaction.atomic():
                claim.status = ShopClaim.Status.VERIFIED
                claim.save(update_fields=["status"])
                
                if claim.shop:
                    claim.shop.is_verified = True
                    claim.shop.owner = claim.user
                    claim.shop.save(update_fields=["is_verified", "owner"])
                    
                    # Add user as owner member
                    ShopMember.objects.get_or_create(
                        shop=claim.shop,
                        user=claim.user,
                        defaults={
                            "role": ShopMember.Role.OWNER,
                            "is_active": True,
                        }
                    )
                
                approved_count += 1
        
        self.message_user(
            request,
            _("%(count)d claim(s) approved.") % {"count": approved_count}
        )
    
    @admin.action(description=_("Reject selected claims"))
    def reject_claims(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.filter(
            status=ShopClaim.Status.PENDING
        ).update(status=ShopClaim.Status.REJECTED)
        
        self.message_user(
            request,
            _("%(count)d claim(s) rejected.") % {"count": updated}
        )
    
    @admin.action(description=_("Reset selected claims to pending"))
    def reset_to_pending(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(status=ShopClaim.Status.PENDING)
        self.message_user(
            request,
            _("%(count)d claim(s) reset to pending.") % {"count": updated}
        )
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        """Claims should be created through the API, not admin."""
        return False


# =============================================================================
# Shop Paper Capability Admin (Standalone)
# =============================================================================


@admin.register(ShopPaperCapability)
class ShopPaperCapabilityAdmin(admin.ModelAdmin):
    """Admin interface for ShopPaperCapability model."""

    list_display = [
        "shop_name",
        "sheet_size",
        "min_gsm",
        "max_gsm",
        "created_at",
    ]
    list_filter = ["sheet_size", "shop"]
    search_fields = ["shop__name"]
    autocomplete_fields = ["shop"]
    list_select_related = ["shop"]
    ordering = ["shop", "sheet_size"]

    @admin.display(description=_("Shop"), ordering="shop__name")
    def shop_name(self, obj: ShopPaperCapability) -> str:
        return obj.shop.name