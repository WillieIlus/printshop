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
    selling_price_duplex_per_sheet = models.DecimalField(
        _("selling price duplex per sheet"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Optional: Price for duplex (both sides) per sheet. If set, overrides 2× per-side for duplex jobs.")
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
        if sides == 2 and self.selling_price_duplex_per_sheet is not None:
            return self.selling_price_duplex_per_sheet
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
# MATERIAL PRICES - Banner, Vinyl, Reflective (large format, priced per SQM)
# =============================================================================

class MaterialPrice(TimeStampedModel):
    """
    Large-format materials priced by area (sqm) or by sheet.
    
    Banner, vinyl, reflective are typically priced per square metre.
    Paper can also be represented here for future flexibility.
    """
    
    class MaterialType(models.TextChoices):
        BANNER = "BANNER", _("Banner")
        VINYL = "VINYL", _("Vinyl")
        REFLECTIVE = "REFLECTIVE", _("Reflective")
        PAPER = "PAPER", _("Paper")
    
    class Unit(models.TextChoices):
        SHEET_A4 = "SHEET_A4", _("Sheet A4")
        SHEET_A3 = "SHEET_A3", _("Sheet A3")
        SHEET_SRA3 = "SHEET_SRA3", _("Sheet SRA3")
        SQM = "SQM", _("Per Square Metre")
    
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="material_prices"
    )
    material_type = models.CharField(
        _("material type"),
        max_length=20,
        choices=MaterialType.choices
    )
    unit = models.CharField(
        _("unit"),
        max_length=20,
        choices=Unit.choices
    )
    selling_price = models.DecimalField(
        _("selling price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("What CUSTOMER pays per unit")
    )
    buying_price = models.DecimalField(
        _("buying price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("What YOU pay per unit (optional)")
    )
    is_active = models.BooleanField(_("active"), default=True)
    
    class Meta:
        verbose_name = _("material price")
        verbose_name_plural = _("material prices")
        ordering = ["material_type", "unit"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "material_type", "unit"],
                name="unique_material_price"
            )
        ]
    
    def __str__(self):
        return f"{self.get_material_type_display()} {self.get_unit_display()}: KES {self.selling_price}"


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
    
    Formula (sheet printing):
    Total = (Printing × Sides × Sheets) + (Paper × Sheets) + Finishing
    
    Formula (large format, unit=SQM):
    Total = (Material × area_sqm) + Finishing
    
    Example: 100 A3 sheets, 300gsm, double-sided, with lamination
    - Printing: 15 × 2 × 100 = 3,000 (or duplex_per_sheet × 100 if override set)
    - Paper: 30 × 100 = 3,000  
    - Lamination: 5 × 100 = 500
    - Total: 6,500
    """
    
    @staticmethod
    def resolve_material_price(shop, material_type: str, unit: str):
        """Resolve MaterialPrice for shop, material_type, unit. Returns None if not found."""
        return MaterialPrice.objects.filter(
            shop=shop,
            material_type=material_type,
            unit=unit,
            is_active=True
        ).first()
    
    @staticmethod
    def calculate(
        shop,
        sheet_size: str = None,
        gsm: int = None,
        quantity: int = 1,
        sides: int = 1,
        paper_type: str = "GLOSS",
        finishing_ids: list = None,
        machine_id: int = None,
        material_type: str = None,
        unit: str = None,
        area_sqm: Decimal = None
    ) -> dict:
        """
        Calculate total price with breakdown.
        
        For sheet printing: provide sheet_size, gsm, quantity, sides, paper_type.
        For large format (SQM): provide material_type, unit="SQM", area_sqm.
        
        Returns dict with:
        - printing_price, paper_price, finishing_price
        - total_printing, total_paper, total_finishing, total_material
        - grand_total, price_per_sheet
        """
        result = {
            "quantity": quantity,
            "sides": sides,
            "printing_price_per_side": Decimal("0"),
            "paper_price_per_sheet": Decimal("0"),
            "total_printing": Decimal("0"),
            "total_paper": Decimal("0"),
            "total_material": Decimal("0"),
            "total_finishing": Decimal("0"),
            "finishing_breakdown": [],
            "grand_total": Decimal("0"),
            "price_per_sheet": Decimal("0"),
        }
        
        # Large format (SQM) path
        if unit == "SQM":
            if material_type is None or area_sqm is None:
                raise ValueError("When unit is SQM, material_type and area_sqm are required")
            material_price = PriceCalculator.resolve_material_price(shop, material_type, "SQM")
            if material_price:
                result["total_material"] = material_price.selling_price * area_sqm
        else:
            # Sheet printing path
            if not sheet_size or gsm is None:
                raise ValueError("Sheet printing requires sheet_size and gsm")
            
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
                if sides == 2:
                    if printing.selling_price_duplex_per_sheet is not None:
                        result["total_printing"] = printing.selling_price_duplex_per_sheet * quantity
                    else:
                        result["total_printing"] = printing.selling_price_per_side * 2 * quantity
                else:
                    result["total_printing"] = printing.selling_price_per_side * quantity
            
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
            result["total_material"] + 
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
