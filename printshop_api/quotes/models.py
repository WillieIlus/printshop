# quotes/models.py
"""
Quote models for customer requests and pricing calculations.
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from common.models import TimeStampedModel
from shops.models import Shop
from inventory.models import Machine, PaperStock
from pricing.models import FinishingService


class ProductTemplate(TimeStampedModel):
    """
    Quick quote presets defined by the shop owner.
    
    Examples:
    - Standard Business Card (85×55mm, 300gsm, duplex)
    - A5 Flyer (148×210mm, 150gsm, simplex)
    """
    
    shop = models.ForeignKey(
        Shop, 
        on_delete=models.CASCADE, 
        related_name="product_templates"
    )
    name = models.CharField(
        _("template name"),
        max_length=150
    )
    description = models.TextField(
        _("description"),
        blank=True
    )
    
    # Default specifications (stored as JSON for flexibility)
    defaults = models.JSONField(
        default=dict, 
        help_text=_("Default settings: {width, height, gsm, sides, finishing_ids}")
    )
    
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("product template")
        verbose_name_plural = _("product templates")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Quote(TimeStampedModel):
    """
    Customer quote request.
    
    Can be created:
    - From a PrintTemplate (customer browsing gallery)
    - From scratch (shop creates quote)
    """
    
    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        PENDING = "PENDING", _("Pending Review")
        SENT = "SENT", _("Sent to Client")
        ACCEPTED = "ACCEPTED", _("Accepted")
        REJECTED = "REJECTED", _("Rejected")
        EXPIRED = "EXPIRED", _("Expired")
        CONVERTED = "CONVERTED", _("Converted to Job")

    shop = models.ForeignKey(
        Shop, 
        on_delete=models.CASCADE, 
        related_name="quotes"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="quotes",
        help_text=_("The customer requesting the quote")
    )
    
    # Link to gallery template (optional)
    source_template = models.ForeignKey(
        "templates.PrintTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes"
    )
    
    # Basic info
    reference = models.CharField(
        _("reference"),
        max_length=50, 
        blank=True, 
        help_text=_("Auto-generated, e.g., Q-202602-0001")
    )
    title = models.CharField(
        _("title"),
        max_length=200,
        blank=True
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.DRAFT
    )
    
    # Notes
    customer_notes = models.TextField(
        _("customer notes"),
        blank=True
    )
    internal_notes = models.TextField(
        _("internal notes"),
        blank=True
    )
    
    # Validity
    valid_until = models.DateField(
        _("valid until"),
        null=True,
        blank=True
    )
    
    # Financials (calculated)
    net_total = models.DecimalField(
        _("subtotal"),
        max_digits=14, 
        decimal_places=2, 
        default=Decimal("0.00")
    )
    tax_rate = models.DecimalField(
        _("tax rate %"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("16.00")
    )
    tax_amount = models.DecimalField(
        _("tax amount"),
        max_digits=14, 
        decimal_places=2, 
        default=Decimal("0.00")
    )
    discount_amount = models.DecimalField(
        _("discount"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00")
    )
    grand_total = models.DecimalField(
        _("grand total"),
        max_digits=14, 
        decimal_places=2, 
        default=Decimal("0.00")
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("quote")
        verbose_name_plural = _("quotes")

    def __str__(self):
        return f"Quote #{self.id} - {self.reference or self.title or 'Untitled'}"

    def save(self, *args, **kwargs):
        # Auto-generate reference
        if not self.reference:
            year = timezone.now().year
            month = timezone.now().month
            count = Quote.objects.filter(
                shop=self.shop,
                created_at__year=year,
                created_at__month=month
            ).count() + 1
            self.reference = f"Q-{year}{month:02d}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        if self.valid_until:
            return timezone.now().date() > self.valid_until
        return False


class QuoteItem(TimeStampedModel):
    """
    Line item in a quote.
    
    Example: "500 Business Cards"
    """
    
    quote = models.ForeignKey(
        Quote, 
        on_delete=models.CASCADE, 
        related_name="items"
    )
    name = models.CharField(
        _("item name"),
        max_length=150, 
        help_text=_("e.g., Business Cards")
    )
    quantity = models.PositiveIntegerField(
        _("quantity"),
        default=1
    )
    
    # Calculated price for this line item
    calculated_price = models.DecimalField(
        _("total price"),
        max_digits=14, 
        decimal_places=2, 
        default=Decimal("0.00")
    )

    class Meta:
        verbose_name = _("quote item")
        verbose_name_plural = _("quote items")

    def __str__(self):
        return f"{self.quantity} × {self.name}"


class QuoteItemPart(TimeStampedModel):
    """
    Physical component of a quote item.
    
    Simple items have 1 part:
    - Flyer: 1 part (the flyer itself)
    
    Complex items have multiple parts:
    - Book: 2 parts (cover + inner pages)
    """
    
    class PrintSides(models.TextChoices):
        SINGLE = "SINGLE", _("Single-sided")
        DOUBLE = "DOUBLE", _("Double-sided")

    item = models.ForeignKey(
        QuoteItem, 
        on_delete=models.CASCADE, 
        related_name="parts"
    )
    name = models.CharField(
        _("part name"),
        max_length=100, 
        help_text=_("e.g., Cover, Inner Pages")
    )
    
    # Final dimensions (after cutting)
    final_width = models.DecimalField(
        _("width (mm)"),
        max_digits=10, 
        decimal_places=2
    )
    final_height = models.DecimalField(
        _("height (mm)"),
        max_digits=10, 
        decimal_places=2
    )

    # Paper selection
    paper_stock = models.ForeignKey(
        PaperStock, 
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text=_("Paper to use from stock")
    )
    
    # Alternative: specify paper directly (for simpler use)
    paper_gsm = models.PositiveIntegerField(
        _("paper GSM"),
        null=True,
        blank=True,
        help_text=_("Paper weight if not using stock")
    )
    
    # Machine and printing
    machine = models.ForeignKey(
        Machine, 
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    print_sides = models.CharField(
        _("print sides"),
        max_length=10, 
        choices=PrintSides.choices, 
        default=PrintSides.SINGLE
    )

    # Imposition results (calculated)
    items_per_sheet = models.PositiveIntegerField(
        _("items per sheet"),
        default=1, 
        help_text=_("How many fit on one sheet")
    )
    total_sheets_required = models.PositiveIntegerField(
        _("sheets required"),
        default=0
    )
    
    # Cost (calculated)
    part_cost = models.DecimalField(
        _("cost"),
        max_digits=14, 
        decimal_places=2, 
        default=Decimal("0.00")
    )

    class Meta:
        verbose_name = _("quote item part")
        verbose_name_plural = _("quote item parts")

    def __str__(self):
        return f"{self.name} ({self.get_print_sides_display()})"


class QuoteItemFinishing(TimeStampedModel):
    """
    Finishing service applied to a quote item.
    
    Example: Lamination, Binding, Cutting
    """
    
    item = models.ForeignKey(
        QuoteItem, 
        on_delete=models.CASCADE, 
        related_name="finishing"
    )
    finishing_service = models.ForeignKey(
        FinishingService, 
        on_delete=models.PROTECT
    )
    
    # Calculated cost
    calculated_cost = models.DecimalField(
        _("cost"),
        max_digits=14, 
        decimal_places=2, 
        default=Decimal("0.00")
    )

    class Meta:
        verbose_name = _("quote item finishing")
        verbose_name_plural = _("quote item finishings")

    def __str__(self):
        return self.finishing_service.name
