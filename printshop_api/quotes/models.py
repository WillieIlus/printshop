# quotes/models.py

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from common.models import TimeStampedModel
from shops.models import Shop
from inventory.models import Machine, Material, MaterialStock
from pricing.models import FinishingPrice

class ProductTemplate(TimeStampedModel):
    """
    Presets defined by the shop owner for quick quoting.
    e.g., "Standard Business Card", "A5 Flyer".
    """
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="product_templates")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    
    # Stores default IDs for machine, material, and standard finishing
    defaults = models.JSONField(default=dict, help_text="JSON Config for default selection")

    def __str__(self):
        return self.name


class Quote(TimeStampedModel):
    """
    The head object representing a customer's request.
    """
    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        SENT = "SENT", _("Sent to Client")
        ACCEPTED = "ACCEPTED", _("Accepted")
        REJECTED = "REJECTED", _("Rejected")
        CONVERTED = "CONVERTED", _("Converted to Job")

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="quotes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quotes")
    reference = models.CharField(max_length=50, blank=True, help_text="Auto-generated Ref ID")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # Financials
    net_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Quote #{self.id} - {self.user}"


class QuoteItem(TimeStampedModel):
    """
    A line item in the quote.
    Represents the final product delivered to the client.
    e.g., "500 x Annual Reports".
    """
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=150, help_text="e.g. Annual Reports")
    quantity = models.PositiveIntegerField(default=1)
    
    # The calculated price for this entire line item
    calculated_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.quantity} x {self.name}"


class QuoteItemPart(TimeStampedModel):
    """
    The physical components that make up an Item.
    A Flyer has 1 Part.
    A Book has 2 Parts: "Cover" and "Inner Pages".
    """
    class PrintSides(models.TextChoices):
        SIMPLEX = "SIMPLEX", _("Simplex (One Side)")
        DUPLEX = "DUPLEX", _("Duplex (Two Sides)")

    item = models.ForeignKey(QuoteItem, on_delete=models.CASCADE, related_name="parts")
    name = models.CharField(max_length=100, help_text="e.g. Cover, Inner Pages")
    
    # The Final Cut Size of this part (e.g., A5 = 148x210mm)
    final_width = models.DecimalField(max_digits=10, decimal_places=2, help_text="Width in mm")
    final_height = models.DecimalField(max_digits=10, decimal_places=2, help_text="Height in mm")

    # Production Specs
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    # Optional: User can specify which exact stock size to use, or logic can guess
    preferred_stock = models.ForeignKey(MaterialStock, on_delete=models.SET_NULL, null=True, blank=True)
    
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT)
    print_sides = models.CharField(max_length=10, choices=PrintSides.choices, default=PrintSides.SIMPLEX)

    # Imposition Results (Calculated & Stored for transparency)
    items_per_sheet = models.PositiveIntegerField(default=1, help_text="N-Up on the stock sheet")
    total_sheets_required = models.PositiveIntegerField(default=0, help_text="Total large sheets needed for the run")
    
    # Financial Breakdown (Snapshotted)
    part_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.name} ({self.print_sides})"


class QuoteItemFinishing(TimeStampedModel):
    """
    Value Added Services attached to the Line Item.
    e.g., "Saddle Stitching" applies to the whole Item (Book).
    e.g., "Lamination" might conceptually apply to the item, calculated via sheet count.
    """
    item = models.ForeignKey(QuoteItem, on_delete=models.CASCADE, related_name="finishing")
    finishing_price = models.ForeignKey(FinishingPrice, on_delete=models.PROTECT)
    
    # Override cost allows ad-hoc adjustments
    calculated_cost = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return self.finishing_price.process_name