# inventory/models.py
"""
Inventory models for print shop.

- Machine: printers/equipment with printing prices (in pricing app)
- Paper: unified paper identity + buy/sell prices + optional stock
"""

from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import TimeStampedModel
from shops.models import Shop


class Machine(TimeStampedModel):
    """
    Printing machines/equipment.
    
    Examples:
    - Xerox Versant 80 (Digital Printer)
    - Canon ImagePRESS (Digital Printer)
    """
    
    class MachineType(models.TextChoices):
        DIGITAL = "DIGITAL", _("Digital Printer")
        LARGE_FORMAT = "LARGE_FORMAT", _("Large Format")
        OFFSET = "OFFSET", _("Offset Press")
        FINISHING = "FINISHING", _("Finishing Equipment")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="machines"
    )
    name = models.CharField(
        _("machine name"),
        max_length=150,
        help_text=_("e.g., Xerox Versant 80")
    )
    machine_type = models.CharField(
        _("type"),
        max_length=20,
        choices=MachineType.choices,
        default=MachineType.DIGITAL
    )
    
    # Optional specs (for compatibility validation at quote-time)
    max_paper_width = models.PositiveIntegerField(
        _("max width (mm)"),
        null=True,
        blank=True,
        help_text=_("Maximum paper width this machine can handle")
    )
    max_paper_height = models.PositiveIntegerField(
        _("max height (mm)"),
        null=True,
        blank=True,
        help_text=_("Maximum paper height this machine can handle")
    )
    
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("machine")
        verbose_name_plural = _("machines")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "name"],
                name="unique_machine_name_per_shop"
            )
        ]

    def __str__(self):
        return self.name


class Paper(TimeStampedModel):
    """
    Unified paper: identity + buy/sell prices + optional stock.
    
    Replaces PaperStock + PaperPrice. One record = one paper type with pricing.
    
    Examples:
    - SRA3 300gsm Gloss: buy KES 18, sell KES 30, 100 sheets in stock
    - A3 130gsm Matte: buy KES 6, sell KES 10 (no stock tracking)
    """
    
    class SheetSize(models.TextChoices):
        A5 = "A5", _("A5 (148 × 210 mm)")
        A4 = "A4", _("A4 (210 × 297 mm)")
        A3 = "A3", _("A3 (297 × 420 mm)")
        SRA3 = "SRA3", _("SRA3 (320 × 450 mm)")
        SRA4 = "SRA4", _("SRA4 (225 × 320 mm)")
    
    class PaperType(models.TextChoices):
        GLOSS = "GLOSS", _("Gloss")
        MATTE = "MATTE", _("Matte")
        BOND = "BOND", _("Bond")
        ART = "ART", _("Art Paper")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="papers"
    )
    sheet_size = models.CharField(
        _("paper size"),
        max_length=20,
        choices=SheetSize.choices,
        default=SheetSize.SRA3
    )
    gsm = models.PositiveIntegerField(
        _("GSM (weight)"),
        validators=[MinValueValidator(60), MaxValueValidator(500)],
        help_text=_("Paper weight: 80, 130, 150, 200, 300, etc.")
    )
    paper_type = models.CharField(
        _("paper type"),
        max_length=20,
        choices=PaperType.choices,
        default=PaperType.GLOSS
    )
    
    # Dimensions (auto-filled from sheet_size)
    width_mm = models.PositiveIntegerField(
        _("width (mm)"),
        null=True,
        blank=True,
        help_text=_("Width in millimeters (auto-filled)")
    )
    height_mm = models.PositiveIntegerField(
        _("height (mm)"),
        null=True,
        blank=True,
        help_text=_("Height in millimeters (auto-filled)")
    )
    
    # Pricing
    buying_price = models.DecimalField(
        _("buying price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("What YOU pay per sheet")
    )
    selling_price = models.DecimalField(
        _("selling price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("What CUSTOMER pays per sheet")
    )
    
    # Optional stock tracking (nullable for shops that don't track)
    quantity_in_stock = models.PositiveIntegerField(
        _("quantity in stock"),
        null=True,
        blank=True,
        default=0,
        help_text=_("Number of sheets in stock (optional)")
    )
    reorder_level = models.PositiveIntegerField(
        _("reorder level"),
        null=True,
        blank=True,
        default=100,
        help_text=_("Order more when stock falls below this (optional)")
    )
    
    is_active = models.BooleanField(_("active"), default=True)
    is_default_seeded = models.BooleanField(_("default seeded"), default=False)
    needs_review = models.BooleanField(_("needs review"), default=False)

    class Meta:
        verbose_name = _("paper")
        verbose_name_plural = _("papers")
        ordering = ["sheet_size", "gsm"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "sheet_size", "gsm", "paper_type"],
                name="unique_paper"
            )
        ]

    def __str__(self):
        stock = f" ({self.quantity_in_stock} sheets)" if self.quantity_in_stock is not None else ""
        return f"{self.get_sheet_size_display()} {self.gsm}gsm {self.get_paper_type_display()}: KES {self.selling_price}{stock}"
    
    def save(self, *args, **kwargs):
        size_dimensions = {
            "A5": (148, 210),
            "A4": (210, 297),
            "A3": (297, 420),
            "SRA3": (320, 450),
            "SRA4": (225, 320),
        }
        if self.sheet_size in size_dimensions and (not self.width_mm or not self.height_mm):
            w, h = size_dimensions[self.sheet_size]
            if not self.width_mm:
                self.width_mm = w
            if not self.height_mm:
                self.height_mm = h
        super().save(*args, **kwargs)
    
    @property
    def needs_reorder(self) -> bool:
        """Check if stock needs to be reordered."""
        if self.quantity_in_stock is None or self.reorder_level is None:
            return False
        return self.quantity_in_stock <= self.reorder_level
    
    @property
    def display_name(self) -> str:
        """Display name for dropdowns."""
        return f"{self.sheet_size} {self.gsm}gsm {self.paper_type}"
    
    @property
    def profit(self) -> Decimal:
        """Profit per sheet."""
        return self.selling_price - self.buying_price
    
    @property
    def margin_percent(self) -> Decimal:
        """Profit margin as percentage."""
        if self.selling_price > 0:
            return ((self.selling_price - self.buying_price) / self.selling_price) * 100
        return Decimal("0")
