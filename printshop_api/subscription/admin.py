# subscription/admin.py

from decimal import Decimal
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    Invoice,
    MpesaStkRequest,
    Payment,
    Subscription,
    SubscriptionPlan,
)


class PaymentInline(admin.TabularInline):
    """Inline for viewing recent payments within a subscription."""
    model = Payment
    extra = 0
    readonly_fields = [
        "amount", "payment_method", "status", "mpesa_receipt_number",
        "payment_date", "period_start", "period_end"
    ]
    can_delete = False
    max_num = 5
    ordering = ["-created_at"]


class InvoiceInline(admin.TabularInline):
    """Inline for viewing invoices within a subscription."""
    model = Invoice
    extra = 0
    readonly_fields = [
        "invoice_number", "issue_date", "due_date", "subtotal",
        "tax_amount", "total", "is_paid"
    ]
    can_delete = False
    max_num = 5
    ordering = ["-issue_date"]


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "plan_type",
        "billing_period",
        "price_display",
        "features_summary",
        "is_active",
    ]
    list_filter = ["plan_type", "billing_period", "is_active"]
    search_fields = ["name"]
    ordering = ["plan_type", "billing_period"]
    list_per_page = 20
    
    fieldsets = (
        (None, {
            "fields": ("name", "plan_type", "billing_period", "price")
        }),
        (_("Limits"), {
            "fields": (
                "max_printing_machines", "max_finishing_machines",
                "max_users", "max_quotes_per_month", "max_products"
            )
        }),
        (_("Features"), {
            "fields": (
                "has_api_access", "has_bulk_operations",
                "has_custom_branding", "has_priority_support"
            )
        }),
        (_("Status"), {
            "fields": ("is_active",)
        }),
    )
    
    @admin.display(description="Price")
    def price_display(self, obj):
        return format_html("<strong>KES {}</strong>", obj.price)
    
    @admin.display(description="Features")
    def features_summary(self, obj):
        features = []
        if obj.has_api_access:
            features.append("API")
        if obj.has_bulk_operations:
            features.append("Bulk")
        if obj.has_custom_branding:
            features.append("Branding")
        if obj.has_priority_support:
            features.append("Support")
        return ", ".join(features) if features else "Basic"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "shop_name",
        "plan_name",
        "status",
        "period_display",
        "next_billing_date",
        "is_locked",
    ]
    list_filter = ["status", "is_locked", "plan__plan_type", "auto_renew"]
    search_fields = ["shop__name", "plan__name"]
    list_select_related = ["shop", "plan"]
    ordering = ["-created_at"]
    list_per_page = 50
    date_hierarchy = "next_billing_date"
    inlines = [PaymentInline, InvoiceInline]
    
    fieldsets = (
        (None, {
            "fields": ("shop", "plan", "status")
        }),
        (_("Billing Dates"), {
            "fields": (
                "start_date", "current_period_start", "current_period_end",
                "trial_end_date", "next_billing_date", "last_payment_date"
            )
        }),
        (_("M-Pesa"), {
            "fields": ("mpesa_shortcode", "mpesa_account_reference"),
            "classes": ("collapse",)
        }),
        (_("Settings"), {
            "fields": ("auto_renew", "is_locked")
        }),
    )
    
    @admin.display(description="Shop", ordering="shop__name")
    def shop_name(self, obj):
        return obj.shop.name
    
    @admin.display(description="Plan", ordering="plan__name")
    def plan_name(self, obj):
        return obj.plan.name
    
    @admin.display(description="Current Period")
    def period_display(self, obj):
        start = obj.current_period_start.strftime("%d %b")
        end = obj.current_period_end.strftime("%d %b %Y")
        return f"{start} - {end}"


@admin.register(MpesaStkRequest)
class MpesaStkRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id", "shop", "plan", "amount", "phone", "status",
        "mpesa_receipt_number", "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["shop__name", "phone", "checkout_request_id"]
    readonly_fields = ["raw_request_payload", "raw_callback_payload"]
    ordering = ["-created_at"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "shop_name",
        "amount_display",
        "payment_method",
        "status",
        "mpesa_receipt_number",
        "payment_date",
        "is_reconciled",
    ]
    list_filter = ["status", "payment_method", "is_reconciled"]
    search_fields = [
        "subscription__shop__name", "mpesa_receipt_number",
        "mpesa_phone_number"
    ]
    list_select_related = ["subscription__shop"]
    ordering = ["-created_at"]
    list_per_page = 50
    date_hierarchy = "payment_date"
    readonly_fields = ["metadata"]
    
    fieldsets = (
        (None, {
            "fields": ("subscription", "amount", "payment_method", "status")
        }),
        (_("M-Pesa Details"), {
            "fields": (
                "mpesa_receipt_number", "mpesa_phone_number",
                "mpesa_request_id", "metadata"
            )
        }),
        (_("Period"), {
            "fields": ("payment_date", "period_start", "period_end")
        }),
        (_("Reconciliation"), {
            "fields": ("is_reconciled", "reconciled_at", "reconciled_by"),
            "classes": ("collapse",)
        }),
        (_("Notes"), {
            "fields": ("description",),
            "classes": ("collapse",)
        }),
    )
    
    @admin.display(description="Shop")
    def shop_name(self, obj):
        return obj.subscription.shop.name
    
    @admin.display(description="Amount")
    def amount_display(self, obj):
        return format_html("<strong>KES {}</strong>", obj.amount)
    
    actions = ["mark_as_reconciled"]
    
    @admin.action(description="Mark selected payments as reconciled")
    def mark_as_reconciled(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            is_reconciled=True,
            reconciled_at=timezone.now(),
            reconciled_by=request.user
        )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number",
        "shop_name",
        "issue_date",
        "due_date",
        "total_display",
        "is_paid",
    ]
    list_filter = ["is_paid", "issue_date"]
    search_fields = ["invoice_number", "subscription__shop__name"]
    list_select_related = ["subscription__shop"]
    ordering = ["-issue_date"]
    list_per_page = 50
    date_hierarchy = "issue_date"
    
    fieldsets = (
        (None, {
            "fields": ("subscription", "payment", "invoice_number")
        }),
        (_("Dates"), {
            "fields": ("issue_date", "due_date")
        }),
        (_("Amounts"), {
            "fields": ("subtotal", "tax_rate", "tax_amount", "total")
        }),
        (_("Status"), {
            "fields": ("is_paid", "notes")
        }),
    )
    
    @admin.display(description="Shop")
    def shop_name(self, obj):
        return obj.subscription.shop.name
    
    @admin.display(description="Total")
    def total_display(self, obj):
        return format_html("<strong>KES {}</strong>", obj.total)
