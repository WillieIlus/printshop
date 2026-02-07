# pricing/models.py
"""
Simplified pricing models with layman-friendly terminology.

Key concepts:
- Buying Price: What the shop pays (cost)
- Selling Price: What the customer pays
- Profit: Selling Price - Buying Price
"""

from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import TimeStampedModel
from shops.models import Shop
from inventory.models import Machine


# =============================================================================
# PRINTING PRICES - What you charge for printing per side
# =============================================================================

class PrintingPrice(TimeStampedModel):
    """
    Printing cost per side (click rate).
    
    Example:
    - A3 Color: KES 15 per side
    - A3 B&W: KES 5 per side
    """
    
    class SheetSize(models.TextChoices):
        A5 = "A5", _("A5")
        A4 = "A4", _("A4")
        A3 = "A3", _("A3")
        SRA3 = "SRA3", _("SRA3")
    
    class ColorMode(models.TextChoices):
        BW = "BW", _("Black & White")
        COLOR = "COLOR", _("Full Color")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="printing_prices"
    )
    machine = models.ForeignKey(
        Machine,
        on_delete=models.PROTECT,
        related_name="printing_prices",
        help_text=_("Which machine/printer")
    )
    sheet_size = models.CharField(
        _("paper size"),
        max_length=20,
        choices=SheetSize.choices,
        default=SheetSize.A4
    )
    color_mode = models.CharField(
        _("color"),
        max_length=20,
        choices=ColorMode.choices,
        default=ColorMode.COLOR
    )
    
    # Simple pricing
    selling_price_per_side = models.DecimalField(
        _("selling price per side"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Price customer pays per printed side")
    )
    buying_price_per_side = models.DecimalField(
        _("buying price per side"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Your cost per side (optional, for tracking profit)")
    )
    
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("printing price")
        verbose_name_plural = _("printing prices")
        ordering = ["sheet_size", "color_mode"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "machine", "sheet_size", "color_mode"],
                name="unique_printing_price"
            )
        ]

    def __str__(self):
        return f"{self.sheet_size} {self.get_color_mode_display()}: KES {self.selling_price_per_side}/side"
    
    @property
    def profit_per_side(self) -> Decimal:
        """Profit per side printed."""
        if self.buying_price_per_side:
            return self.selling_price_per_side - self.buying_price_per_side
        return Decimal("0")
    
    def get_price_for_sides(self, sides: int = 1) -> Decimal:
        """Get price for 1 or 2 sides."""
        return self.selling_price_per_side * sides


# =============================================================================
# PAPER PRICES - What you charge for paper by GSM
# =============================================================================

class PaperPrice(TimeStampedModel):
    """
    Simple paper pricing by weight (GSM).
    
    Example rate card:
    - 130 GSM: Buy KES 6, Sell KES 10
    - 150 GSM: Buy KES 9, Sell KES 15
    - 200 GSM: Buy KES 12, Sell KES 20
    - 300 GSM: Buy KES 18, Sell KES 30
    
    Total = Printing Price + Paper Price
    """
    
    class SheetSize(models.TextChoices):
        A5 = "A5", _("A5")
        A4 = "A4", _("A4")
        A3 = "A3", _("A3")
        SRA3 = "SRA3", _("SRA3")
    
    class PaperType(models.TextChoices):
        GLOSS = "GLOSS", _("Gloss")
        MATTE = "MATTE", _("Matte")
        BOND = "BOND", _("Bond")
        ART = "ART", _("Art Paper")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="paper_prices"
    )
    sheet_size = models.CharField(
        _("paper size"),
        max_length=20,
        choices=SheetSize.choices,
        default=SheetSize.A3
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
    
    # Simple pricing - clear terminology
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
    
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("paper price")
        verbose_name_plural = _("paper prices")
        ordering = ["sheet_size", "gsm"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "sheet_size", "gsm", "paper_type"],
                name="unique_paper_price"
            )
        ]

    def __str__(self):
        return f"{self.sheet_size} {self.gsm}gsm {self.get_paper_type_display()}: KES {self.selling_price}"
    
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


# =============================================================================
# FINISHING PRICES - Lamination, Binding, Cutting, etc.
# =============================================================================

class FinishingService(TimeStampedModel):
    """
    Finishing services with simple pricing.
    
    Examples:
    - Matt Lamination A3: KES 5 per sheet
    - Binding (Spiral): KES 50 per book
    - Cutting: KES 30 per job
    """
    
    class Category(models.TextChoices):
        LAMINATION = "LAMINATION", _("Lamination")
        BINDING = "BINDING", _("Binding")
        CUTTING = "CUTTING", _("Cutting")
        FOLDING = "FOLDING", _("Folding")
        OTHER = "OTHER", _("Other")
    
    class ChargeBy(models.TextChoices):
        PER_SHEET = "PER_SHEET", _("Per Sheet")
        PER_PIECE = "PER_PIECE", _("Per Piece/Item")
        PER_JOB = "PER_JOB", _("Per Job (Flat Fee)")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="finishing_services"
    )
    name = models.CharField(
        _("service name"),
        max_length=100,
        help_text=_("e.g., Matt Lamination A3, Spiral Binding")
    )
    category = models.CharField(
        _("category"),
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER
    )
    charge_by = models.CharField(
        _("charge by"),
        max_length=20,
        choices=ChargeBy.choices,
        default=ChargeBy.PER_SHEET
    )
    
    # Simple pricing
    buying_price = models.DecimalField(
        _("buying price"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Your cost (if any)")
    )
    selling_price = models.DecimalField(
        _("selling price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Price customer pays")
    )
    
    # Optional: pre-selected for certain products
    is_default = models.BooleanField(
        _("selected by default"),
        default=False,
        help_text=_("Pre-select this option for customers")
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("finishing service")
        verbose_name_plural = _("finishing services")
        ordering = ["category", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "name"],
                name="unique_finishing_service"
            )
        ]

    def __str__(self):
        return f"{self.name}: KES {self.selling_price} {self.get_charge_by_display()}"
    
    @property
    def profit(self) -> Decimal:
        """Profit per unit."""
        return self.selling_price - self.buying_price
    
    def calculate_total(self, quantity: int = 1) -> Decimal:
        """Calculate total for given quantity."""
        if self.charge_by == self.ChargeBy.PER_JOB:
            return self.selling_price
        return self.selling_price * quantity


# =============================================================================
# SIMPLE PRICE CALCULATOR - Combines everything
# =============================================================================

class PriceCalculator:
    """
    Helper class to calculate total price.
    
    Formula:
    Total = (Printing × Sides × Sheets) + (Paper × Sheets) + Finishing
    
    Example: 100 A3 sheets, 300gsm, double-sided, with lamination
    - Printing: 15 × 2 × 100 = 3,000
    - Paper: 30 × 100 = 3,000  
    - Lamination: 5 × 100 = 500
    - Total: 6,500
    """
    
    @staticmethod
    def calculate(
        shop,
        sheet_size: str,
        gsm: int,
        quantity: int,
        sides: int = 1,
        paper_type: str = "GLOSS",
        finishing_ids: list = None,
        machine_id: int = None
    ) -> dict:
        """
        Calculate total price with breakdown.
        
        Returns dict with:
        - printing_price, paper_price, finishing_price
        - total_printing, total_paper, total_finishing
        - grand_total, price_per_sheet
        """
        result = {
            "quantity": quantity,
            "sides": sides,
            "printing_price_per_side": Decimal("0"),
            "paper_price_per_sheet": Decimal("0"),
            "total_printing": Decimal("0"),
            "total_paper": Decimal("0"),
            "total_finishing": Decimal("0"),
            "finishing_breakdown": [],
            "grand_total": Decimal("0"),
            "price_per_sheet": Decimal("0"),
        }
        
        # Get printing price
        printing_filter = {
            "shop": shop,
            "sheet_size": sheet_size,
            "is_active": True
        }
        if machine_id:
            printing_filter["machine_id"] = machine_id
            
        printing = PrintingPrice.objects.filter(**printing_filter).first()
        if printing:
            result["printing_price_per_side"] = printing.selling_price_per_side
            result["total_printing"] = printing.selling_price_per_side * sides * quantity
        
        # Get paper price
        try:
            paper = PaperPrice.objects.get(
                shop=shop,
                sheet_size=sheet_size,
                gsm=gsm,
                paper_type=paper_type,
                is_active=True
            )
            result["paper_price_per_sheet"] = paper.selling_price
            result["total_paper"] = paper.selling_price * quantity
        except PaperPrice.DoesNotExist:
            pass
        
        # Get finishing prices
        if finishing_ids:
            finishes = FinishingService.objects.filter(
                shop=shop,
                id__in=finishing_ids,
                is_active=True
            )
            for finish in finishes:
                cost = finish.calculate_total(quantity)
                result["finishing_breakdown"].append({
                    "name": finish.name,
                    "price": finish.selling_price,
                    "charge_by": finish.charge_by,
                    "total": cost
                })
                result["total_finishing"] += cost
        
        # Calculate totals
        result["grand_total"] = (
            result["total_printing"] + 
            result["total_paper"] + 
            result["total_finishing"]
        )
        
        if quantity > 0:
            result["price_per_sheet"] = result["grand_total"] / quantity
        
        return result


# =============================================================================
# LEGACY COMPATIBILITY - Keep old models working during transition
# =============================================================================

# Alias for backward compatibility with existing code
DigitalPrintPrice = PrintingPrice
PaperGSMPrice = PaperPrice
FinishingPrice = FinishingService


# =============================================================================
# OPTIONAL: Volume Discounts (Advanced Feature)
# =============================================================================

class VolumeDiscount(TimeStampedModel):
    """
    Optional bulk discounts.
    
    Example: 10% off orders over 500 sheets
    """
    
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="volume_discounts"
    )
    name = models.CharField(
        _("name"),
        max_length=100,
        help_text=_("e.g., Bulk Order 10% Off")
    )
    min_quantity = models.PositiveIntegerField(
        _("minimum quantity"),
        default=100,
        help_text=_("Minimum sheets/items to qualify")
    )
    discount_percent = models.DecimalField(
        _("discount %"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("10"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text=_("Percentage discount (e.g., 10 for 10%)")
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("volume discount")
        verbose_name_plural = _("volume discounts")
        ordering = ["min_quantity"]

    def __str__(self):
        return f"{self.name}: {self.discount_percent}% off for {self.min_quantity}+ items"
    
    def apply(self, total: Decimal) -> Decimal:
        """Apply discount to total."""
        discount = total * (self.discount_percent / 100)
        return total - discount
