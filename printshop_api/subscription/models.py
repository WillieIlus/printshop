# subscriptions/models.py

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.models import TimeStampedModel
from shops.models import Shop


class SubscriptionPlan(TimeStampedModel):
    """
    Defines available subscription tiers for shops.
    """
    
    class PlanType(models.TextChoices):
        STARTER = "STARTER", _("Starter")
        PROFESSIONAL = "PROFESSIONAL", _("Professional")
        ENTERPRISE = "ENTERPRISE", _("Enterprise")
    
    class BillingPeriod(models.TextChoices):
        WEEKLY = "WEEKLY", _("Weekly")
        BIWEEKLY = "BIWEEKLY", _("Bi-Weekly (Fortnightly)")
        MONTHLY = "MONTHLY", _("Monthly")
    
    name = models.CharField(_("plan name"), max_length=100)
    plan_type = models.CharField(
        _("plan type"),
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.STARTER
    )
    billing_period = models.CharField(
        _("billing period"),
        max_length=20,
        choices=BillingPeriod.choices,
        default=BillingPeriod.MONTHLY
    )
    price = models.DecimalField(
        _("price (KES)"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Price in Kenya Shillings")
    )
    
    # Plan Features/Limits
    max_users = models.PositiveIntegerField(
        _("max users"),
        default=1,
        help_text=_("Maximum staff accounts allowed")
    )
    max_quotes_per_month = models.PositiveIntegerField(
        _("max quotes/month"),
        default=100,
        help_text=_("Maximum quotes per month. 0 = unlimited")
    )
    max_products = models.PositiveIntegerField(
        _("max products"),
        default=50,
        help_text=_("Maximum product templates. 0 = unlimited")
    )
    
    # Features
    has_api_access = models.BooleanField(_("API access"), default=False)
    has_bulk_operations = models.BooleanField(_("bulk operations"), default=False)
    has_custom_branding = models.BooleanField(_("custom branding"), default=False)
    has_priority_support = models.BooleanField(_("priority support"), default=False)
    
    is_active = models.BooleanField(_("active"), default=True)
    
    class Meta:
        verbose_name = _("subscription plan")
        verbose_name_plural = _("subscription plans")
        ordering = ["price"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan_type", "billing_period"],
                name="unique_plan_per_type_period"
            )
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_billing_period_display()} ({self.price} KES)"
    
    @property
    def days_in_period(self) -> int:
        """Return the number of days in the billing period."""
        return {
            self.BillingPeriod.WEEKLY: 7,
            self.BillingPeriod.BIWEEKLY: 14,
            self.BillingPeriod.MONTHLY: 30,
        }.get(self.billing_period, 30)


class Subscription(TimeStampedModel):
    """
    Links a Shop to a SubscriptionPlan with billing history.
    """
    
    class Status(models.TextChoices):
        TRIAL = "TRIAL", _("Trial")
        ACTIVE = "ACTIVE", _("Active")
        PAST_DUE = "PAST_DUE", _("Past Due")
        CANCELLED = "CANCELLED", _("Cancelled")
        EXPIRED = "EXPIRED", _("Expired")
    
    shop = models.OneToOneField(
        Shop,
        on_delete=models.CASCADE,
        related_name="subscription"
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL
    )
    
    # Billing Dates
    start_date = models.DateTimeField(_("start date"), default=timezone.now)
    current_period_start = models.DateTimeField(_("current period start"))
    current_period_end = models.DateTimeField(_("current period end"))
    trial_end_date = models.DateTimeField(
        _("trial end date"),
        null=True,
        blank=True,
        help_text=_("When the free trial ends")
    )
    
    # M-Pesa Integration
    mpesa_shortcode = models.CharField(
        _("M-Pesa paybill/till"),
        max_length=20,
        blank=True,
        help_text=_("Shop's M-Pesa collection number")
    )
    mpesa_account_reference = models.CharField(
        _("account reference"),
        max_length=50,
        blank=True,
        help_text=_("Reference for M-Pesa payments")
    )
    
    # Billing
    next_billing_date = models.DateTimeField(_("next billing date"))
    last_payment_date = models.DateTimeField(
        _("last payment date"),
        null=True,
        blank=True
    )
    
    # Flags
    auto_renew = models.BooleanField(_("auto renew"), default=True)
    is_locked = models.BooleanField(
        _("locked"),
        default=False,
        help_text=_("Lock access if payment fails")
    )
    
    class Meta:
        verbose_name = _("subscription")
        verbose_name_plural = _("subscriptions")
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.shop.name} - {self.plan.name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        if not self.current_period_start:
            self.current_period_start = self.start_date
        if not self.current_period_end:
            self.current_period_end = self.calculate_period_end(self.current_period_start)
        if not self.next_billing_date:
            self.next_billing_date = self.current_period_end
        super().save(*args, **kwargs)
    
    def calculate_period_end(self, start_date):
        """Calculate the end date based on the plan's billing period."""
        from datetime import timedelta
        days = self.plan.days_in_period
        return start_date + timedelta(days=days)
    
    def is_feature_available(self, feature_name: str) -> bool:
        """Check if a specific feature is available in the current plan."""
        if self.status not in [self.Status.ACTIVE, self.Status.TRIAL]:
            return False
        return getattr(self.plan, feature_name, False)


class Payment(TimeStampedModel):
    """
    Records all subscription payments.
    """
    
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        PROCESSING = "PROCESSING", _("Processing")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")
        REFUNDED = "REFUNDED", _("Refunded")
    
    class PaymentMethod(models.TextChoices):
        MPESA_B2B = "MPESA_B2B", _("M-Pesa Business")
        MPESA_C2B = "MPESA_C2B", _("M-Pesa Customer")
        BANK_TRANSFER = "BANK_TRANSFER", _("Bank Transfer")
        CASH = "CASH", _("Cash")
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    amount = models.DecimalField(
        _("amount (KES)"),
        max_digits=10,
        decimal_places=2
    )
    payment_method = models.CharField(
        _("payment method"),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MPESA_B2B
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    # M-Pesa Specific Fields
    mpesa_receipt_number = models.CharField(
        _("M-Pesa receipt"),
        max_length=50,
        blank=True,
        unique=True,
        null=True,
        help_text=_("M-Pesa transaction ID")
    )
    mpesa_phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        blank=True,
        help_text=_("Phone number used for payment")
    )
    mpesa_request_id = models.CharField(
        _("request ID"),
        max_length=100,
        blank=True,
        help_text=_("Internal M-Pesa API request ID")
    )
    
    # Dates
    payment_date = models.DateTimeField(
        _("payment date"),
        null=True,
        blank=True
    )
    period_start = models.DateTimeField(_("period start"))
    period_end = models.DateTimeField(_("period end"))
    
    # Metadata
    description = models.TextField(_("description"), blank=True)
    metadata = models.JSONField(
        _("metadata"),
        default=dict,
        blank=True,
        help_text=_("Store M-Pesa callback data")
    )
    
    # Reconciliation
    is_reconciled = models.BooleanField(
        _("reconciled"),
        default=False,
        help_text=_("Has this payment been verified?")
    )
    reconciled_at = models.DateTimeField(
        _("reconciled at"),
        null=True,
        blank=True
    )
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reconciled_payments"
    )
    
    class Meta:
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["mpesa_receipt_number"]),
            models.Index(fields=["status", "payment_date"]),
        ]
    
    def __str__(self):
        return f"{self.subscription.shop.name} - {self.amount} KES - {self.get_status_display()}"
    
    def mark_as_completed(self):
        """Mark payment as completed and update subscription."""
        self.status = self.PaymentStatus.COMPLETED
        self.payment_date = timezone.now()
        self.save()
        
        # Update subscription
        sub = self.subscription
        sub.last_payment_date = self.payment_date
        sub.status = Subscription.Status.ACTIVE
        sub.is_locked = False
        sub.current_period_start = self.period_start
        sub.current_period_end = self.period_end
        sub.next_billing_date = self.period_end
        sub.save()


class Invoice(TimeStampedModel):
    """
    Generates invoices for subscription payments.
    """
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="invoices"
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice"
    )
    
    invoice_number = models.CharField(
        _("invoice number"),
        max_length=50,
        unique=True
    )
    issue_date = models.DateField(_("issue date"), default=timezone.now)
    due_date = models.DateField(_("due date"))
    
    subtotal = models.DecimalField(
        _("subtotal"),
        max_digits=10,
        decimal_places=2
    )
    tax_rate = models.DecimalField(
        _("VAT rate"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("16.00"),
        help_text=_("Kenya VAT rate")
    )
    tax_amount = models.DecimalField(
        _("VAT amount"),
        max_digits=10,
        decimal_places=2
    )
    total = models.DecimalField(
        _("total"),
        max_digits=10,
        decimal_places=2
    )
    
    is_paid = models.BooleanField(_("paid"), default=False)
    notes = models.TextField(_("notes"), blank=True)
    
    class Meta:
        verbose_name = _("invoice")
        verbose_name_plural = _("invoices")
        ordering = ["-issue_date", "-invoice_number"]
    
    def __str__(self):
        return f"Invoice {self.invoice_number}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            year = timezone.now().year
            month = timezone.now().month
            count = Invoice.objects.filter(
                issue_date__year=year,
                issue_date__month=month
            ).count() + 1
            self.invoice_number = f"INV-{year}{month:02d}-{count:04d}"
        
        # Calculate tax
        if self.subtotal and not self.tax_amount:
            self.tax_amount = self.subtotal * (self.tax_rate / 100)
            self.total = self.subtotal + self.tax_amount
        
        super().save(*args, **kwargs)