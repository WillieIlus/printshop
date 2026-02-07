# inventory/models.py
"""
Simplified inventory models for print shop.

Two main things a print shop needs to track:
1. Machines - The printers/equipment
2. Paper Stock - What paper sizes are available

For pricing, use the pricing app (PaperPrice, PrintingPrice, etc.)
"""

from django.core.exceptions import ValidationError
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
    - Laminator
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
    
    # Optional specs
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
        return f"{self.name}"


class PaperStock(TimeStampedModel):
    """
    Paper stock in inventory.
    
    Tracks what paper sizes and types are available.
    For complex jobs that need imposition calculations.
    
    Examples:
    - SRA3 300gsm Gloss (100 sheets in stock)
    - A3 130gsm Matte (500 sheets in stock)
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
        related_name="paper_stock"
    )
    sheet_size = models.CharField(
        _("paper size"),
        max_length=20,
        choices=SheetSize.choices,
        default=SheetSize.SRA3
    )
    gsm = models.PositiveIntegerField(
        _("GSM (weight)"),
        help_text=_("Paper weight: 80, 130, 150, 200, 300, etc.")
    )
    paper_type = models.CharField(
        _("paper type"),
        max_length=20,
        choices=PaperType.choices,
        default=PaperType.GLOSS
    )
    
    # Dimensions (auto-filled based on sheet_size, or custom)
    width_mm = models.PositiveIntegerField(
        _("width (mm)"),
        help_text=_("Width in millimeters")
    )
    height_mm = models.PositiveIntegerField(
        _("height (mm)"),
        help_text=_("Height in millimeters")
    )
    
    # Stock tracking
    quantity_in_stock = models.PositiveIntegerField(
        _("quantity in stock"),
        default=0,
        help_text=_("Number of sheets currently in stock")
    )
    reorder_level = models.PositiveIntegerField(
        _("reorder level"),
        default=100,
        help_text=_("Order more when stock falls below this level")
    )
    
    # Cost tracking (optional)
    buying_price_per_sheet = models.DecimalField(
        _("buying price per sheet"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Your cost per sheet")
    )
    
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("paper stock")
        verbose_name_plural = _("paper stocks")
        ordering = ["sheet_size", "gsm"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "sheet_size", "gsm", "paper_type"],
                name="unique_paper_stock"
            )
        ]

    def __str__(self):
        return f"{self.get_sheet_size_display()} {self.gsm}gsm {self.get_paper_type_display()} ({self.quantity_in_stock} sheets)"
    
    def save(self, *args, **kwargs):
        # Auto-fill dimensions based on sheet size
        size_dimensions = {
            "A5": (148, 210),
            "A4": (210, 297),
            "A3": (297, 420),
            "SRA3": (320, 450),
            "SRA4": (225, 320),
        }
        if self.sheet_size in size_dimensions and not self.width_mm:
            self.width_mm, self.height_mm = size_dimensions[self.sheet_size]
        super().save(*args, **kwargs)
    
    @property
    def needs_reorder(self) -> bool:
        """Check if stock needs to be reordered."""
        return self.quantity_in_stock <= self.reorder_level
    
    @property
    def display_name(self) -> str:
        """Display name for dropdowns."""
        return f"{self.sheet_size} {self.gsm}gsm {self.paper_type}"


# =============================================================================
# LEGACY COMPATIBILITY - Keep old model names working
# =============================================================================

# Aliases for backward compatibility with existing code
Material = PaperStock
MaterialStock = PaperStock


# Legacy model for complex material definitions (deprecated)
class MachineCapability(TimeStampedModel):
    """
    DEPRECATED: Use Machine.max_paper_width/height instead.
    Keeping for migration compatibility.
    """
    
    class FeedType(models.TextChoices):
        SHEET_FED = "SHEET_FED", _("Sheet Fed")
        ROLL_FED = "ROLL_FED", _("Roll Fed")
        FLATBED = "FLATBED", _("Flatbed")

    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name="capabilities"
    )
    feed_type = models.CharField(
        max_length=20,
        choices=FeedType.choices,
        default=FeedType.SHEET_FED
    )
    max_width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    max_height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _("machine capability (legacy)")
        verbose_name_plural = _("machine capabilities (legacy)")

    def __str__(self):
        return f"{self.machine.name} - {self.get_feed_type_display()}"
