# pricing/models.py

from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import TimeStampedModel
from shops.models import Shop
from inventory.models import Machine, Material


class DigitalPrintPrice(TimeStampedModel):
    """
    Defines the cost of printing on a specific machine.
    Supports separate rates for simplex (Side 1) and duplex (Side 1 + Side 2).
    """
    
    class SheetSize(models.TextChoices):
        A4 = "A4", _("A4 (210 x 297 mm)")
        A3 = "A3", _("A3 (297 x 420 mm)")
        SRA3 = "SRA3", _("SRA3 (320 x 450 mm)")
        SRA4 = "SRA4", _("SRA4 (225 x 320 mm)")
        A5 = "A5", _("A5 (148 x 210 mm)")
        LETTER = "LETTER", _("Letter (8.5 x 11 in)")
        LEGAL = "LEGAL", _("Legal (8.5 x 14 in)")
        TABLOID = "TABLOID", _("Tabloid (11 x 17 in)")
    
    class ColorMode(models.TextChoices):
        BW = "BW", _("Black & White")
        COLOR = "COLOR", _("Full Color")
        SPOT = "SPOT", _("Spot Color")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="digital_print_prices",
        help_text=_("The shop this pricing belongs to.")
    )
    machine = models.ForeignKey(
        Machine,
        on_delete=models.PROTECT,
        related_name="print_prices",
        help_text=_("The machine this price applies to.")
    )
    sheet_size = models.CharField(
        _("sheet size"),
        max_length=20,
        choices=SheetSize.choices,
        default=SheetSize.A4
    )
    color_mode = models.CharField(
        _("color mode"),
        max_length=20,
        choices=ColorMode.choices,
        default=ColorMode.COLOR
    )
    click_rate = models.DecimalField(
        _("click rate"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Cost per impression/click (one side of paper).")
    )
    duplex_rate = models.DecimalField(
        _("duplex rate"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Optional rate for double-sided printing. If null, defaults to 2x click_rate.")
    )
    minimum_order_quantity = models.PositiveIntegerField(
        _("minimum order quantity"),
        default=1,
        help_text=_("Minimum number of impressions for this rate.")
    )
    is_active = models.BooleanField(
        _("active"),
        default=True
    )

    class Meta:
        verbose_name = _("digital print price")
        verbose_name_plural = _("digital print prices")
        ordering = ["machine__name", "sheet_size"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "machine", "sheet_size", "color_mode"],
                name="unique_print_price_per_shop_machine_size_color"
            )
        ]

    def __str__(self):
        return f"{self.machine.name} - {self.sheet_size} ({self.get_color_mode_display()}): {self.click_rate}"

    @property
    def effective_duplex_rate(self) -> Decimal:
        """Return duplex rate or calculate from click rate."""
        if self.duplex_rate:
            return self.duplex_rate
        return self.click_rate * 2

    def calculate_cost(self, quantity: int, duplex: bool = False) -> Decimal:
        """Calculate total printing cost for given quantity."""
        rate = self.effective_duplex_rate if duplex else self.click_rate
        return rate * max(quantity, self.minimum_order_quantity)


class MaterialPrice(TimeStampedModel):
    """
    Defines the selling price for materials/substrates.
    Can use either fixed price or markup-based pricing.
    """
    
    class PricingMethod(models.TextChoices):
        FIXED = "FIXED", _("Fixed Price")
        MARKUP = "MARKUP", _("Markup on Cost")
        MARGIN = "MARGIN", _("Profit Margin")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="material_prices",
        help_text=_("The shop this pricing belongs to.")
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="selling_prices",
        help_text=_("The material this price applies to.")
    )
    pricing_method = models.CharField(
        _("pricing method"),
        max_length=20,
        choices=PricingMethod.choices,
        default=PricingMethod.FIXED
    )
    selling_price_per_unit = models.DecimalField(
        _("selling price per unit"),
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Fixed selling price. Required if pricing method is FIXED.")
    )
    markup_percentage = models.DecimalField(
        _("markup percentage"),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("1000"))],
        help_text=_("Markup percentage on cost price (e.g., 50 for 50%). Used if method is MARKUP.")
    )
    margin_percentage = models.DecimalField(
        _("margin percentage"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("99.99"))],
        help_text=_("Target profit margin (e.g., 30 for 30%). Used if method is MARGIN.")
    )
    minimum_order_value = models.DecimalField(
        _("minimum order value"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Minimum charge for this material.")
    )
    is_active = models.BooleanField(
        _("active"),
        default=True
    )

    class Meta:
        verbose_name = _("material price")
        verbose_name_plural = _("material prices")
        ordering = ["material__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "material"],
                name="unique_material_price_per_shop"
            )
        ]

    def __str__(self):
        return f"{self.material.name}: {self.calculated_selling_price}"

    @property
    def calculated_selling_price(self) -> Decimal:
        """Calculate the effective selling price based on pricing method."""
        if self.pricing_method == self.PricingMethod.FIXED:
            return self.selling_price_per_unit or Decimal("0")
        
        cost = self.material.cost_per_unit
        
        if self.pricing_method == self.PricingMethod.MARKUP:
            markup = self.markup_percentage or Decimal("0")
            return cost * (1 + markup / 100)
        
        if self.pricing_method == self.PricingMethod.MARGIN:
            margin = self.margin_percentage or Decimal("0")
            if margin >= 100:
                return cost * 10  # Fallback for invalid margin
            return cost / (1 - margin / 100)
        
        return self.selling_price_per_unit or Decimal("0")

    @property
    def profit_per_unit(self) -> Decimal:
        """Calculate profit per unit."""
        return self.calculated_selling_price - self.material.cost_per_unit

    @property
    def effective_margin_percentage(self) -> Decimal:
        """Calculate effective margin regardless of pricing method."""
        selling = self.calculated_selling_price
        if selling <= 0:
            return Decimal("0")
        return ((selling - self.material.cost_per_unit) / selling) * 100


class FinishingPrice(TimeStampedModel):
    """
    Defines prices for finishing processes (lamination, binding, cutting, etc.).
    """
    
    class FinishingCategory(models.TextChoices):
        LAMINATION = "LAMINATION", _("Lamination")
        BINDING = "BINDING", _("Binding")
        CUTTING = "CUTTING", _("Cutting")
        CREASING = "CREASING", _("Creasing/Scoring")
        FOLDING = "FOLDING", _("Folding")
        OTHER = "OTHER", _("Other")

    class PricingUnit(models.TextChoices):
        PER_SHEET = "PER_SHEET", _("Per Sheet")
        PER_SIDE = "PER_SIDE", _("Per Side (For Lamination)")
        PER_JOB = "PER_JOB", _("Per Job (Flat Fee)")
        PER_PIECE = "PER_PIECE", _("Per Finished Item")
        PER_BATCH = "PER_BATCH", _("Per Batch")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="finishing_prices"
    )
    process_name = models.CharField(
        _("process name"),
        max_length=150,
        help_text=_("e.g., 'Matt Lamination SRA3', 'Saddle Stitch Binding'")
    )
    category = models.CharField(
        _("category"),
        max_length=30,
        choices=FinishingCategory.choices,
        default=FinishingCategory.OTHER
    )
    unit = models.CharField(
        _("pricing unit"),
        max_length=20,
        choices=PricingUnit.choices,
        default=PricingUnit.PER_SHEET
    )
    price = models.DecimalField(
        _("price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Base price per unit.")
    )
    batch_size = models.PositiveIntegerField(
        _("batch size"),
        default=1,
        help_text=_("If unit is 'Per Batch', define size (e.g., 1000 for 'per 1000 sheets').")
    )
    setup_fee = models.DecimalField(
        _("setup fee"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("One-time setup fee.")
    )
    minimum_order_quantity = models.PositiveIntegerField(
        _("minimum order quantity"),
        default=1
    )
    is_active = models.BooleanField(
        _("active"),
        default=True
    )

    class Meta:
        verbose_name = _("finishing price")
        verbose_name_plural = _("finishing prices")
        ordering = ["category", "process_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "process_name"],
                name="unique_finishing_price_per_shop"
            )
        ]

    def __str__(self):
        return f"{self.process_name}: {self.price} {self.get_unit_display()}"

    def calculate_cost(self, quantity: int = 1, include_setup: bool = True) -> Decimal:
        """Calculate total cost for finishing process."""
        import math
        
        qty = max(quantity, self.minimum_order_quantity)
        
        if self.unit == self.PricingUnit.PER_BATCH:
            # Ceiling division for batches (guard against zero batch_size)
            effective_batch = max(1, self.batch_size)
            batches = math.ceil(qty / effective_batch)
            total = self.price * batches
        elif self.unit == self.PricingUnit.PER_JOB:
            total = self.price
        else:
            total = self.price * qty
        
        if include_setup:
            total += self.setup_fee
        
        return total


class PricingTier(TimeStampedModel):
    """
    Handles bulk/tiered pricing for finishing services.
    Example: 
    - Binding 1-50 books: 50 KSH each
    - Binding 51-100 books: 40 KSH each
    - Binding 101+: 30 KSH each
    """
    
    finishing_service = models.ForeignKey(
        FinishingPrice,
        on_delete=models.CASCADE,
        related_name="tiers"
    )
    min_quantity = models.PositiveIntegerField(
        _("min quantity"),
        default=1,
        help_text=_("Start of the quantity range.")
    )
    max_quantity = models.PositiveIntegerField(
        _("max quantity"),
        null=True,
        blank=True,
        help_text=_("End of the quantity range. Leave blank for unlimited (e.g., 100+).")
    )
    price_per_unit = models.DecimalField(
        _("price per unit"),
        max_digits=10,
        decimal_places=2,
        help_text=_("The rate applied within this range.")
    )

    class Meta:
        verbose_name = _("pricing tier")
        verbose_name_plural = _("pricing tiers")
        ordering = ["finishing_service", "min_quantity"]
        constraints = [
            models.UniqueConstraint(
                fields=["finishing_service", "min_quantity"],
                name="unique_tier_start_per_service"
            )
        ]

    def __str__(self):
        max_display = self.max_quantity or "∞"
        return f"{self.finishing_service.process_name}: {self.min_quantity}-{max_display} @ {self.price_per_unit}"


class VolumeDiscount(TimeStampedModel):
    """
    Volume-based discounts that can apply to print or material pricing.
    """
    
    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", _("Percentage Off")
        FIXED_RATE = "FIXED_RATE", _("Fixed Rate Override")
        AMOUNT_OFF = "AMOUNT_OFF", _("Fixed Amount Off")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="volume_discounts"
    )
    name = models.CharField(
        _("discount name"),
        max_length=100,
        help_text=_("e.g., 'Bulk Print Discount', '500+ Sheets'")
    )
    minimum_quantity = models.PositiveIntegerField(
        _("minimum quantity"),
        help_text=_("Minimum quantity to trigger this discount.")
    )
    maximum_quantity = models.PositiveIntegerField(
        _("maximum quantity"),
        null=True,
        blank=True,
        help_text=_("Maximum quantity for this tier. Leave blank for unlimited.")
    )
    discount_type = models.CharField(
        _("discount type"),
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE
    )
    discount_value = models.DecimalField(
        _("discount value"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Percentage, fixed rate, or amount based on discount type.")
    )
    applies_to_print = models.BooleanField(
        _("applies to print"),
        default=True
    )
    applies_to_material = models.BooleanField(
        _("applies to material"),
        default=False
    )
    applies_to_finishing = models.BooleanField(
        _("applies to finishing"),
        default=False
    )
    is_active = models.BooleanField(
        _("active"),
        default=True
    )

    class Meta:
        verbose_name = _("volume discount")
        verbose_name_plural = _("volume discounts")
        ordering = ["minimum_quantity"]

    def __str__(self):
        return f"{self.name}: {self.discount_value} ({self.get_discount_type_display()})"

    def apply_discount(self, base_price: Decimal) -> Decimal:
        """Apply discount to a base price and return discounted price."""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discounted = base_price * (1 - self.discount_value / 100)
            return max(discounted, Decimal("0"))
        elif self.discount_type == self.DiscountType.FIXED_RATE:
            return max(self.discount_value, Decimal("0"))
        elif self.discount_type == self.DiscountType.AMOUNT_OFF:
            return max(base_price - self.discount_value, Decimal("0"))
        return base_price


# =============================================================================
# Pricing engine (centralized rates + instant quote)
# =============================================================================


class PricingVariable(TimeStampedModel):
    """
    Centralized rates that apply everywhere instantly.
    e.g. "Digital Print Margin", "global-margin".
    """

    name = models.CharField(
        _("name"),
        max_length=100,
        help_text=_("e.g., Digital Print Margin"),
    )
    key = models.SlugField(
        _("key"),
        unique=True,
        max_length=100,
        help_text=_("Unique identifier, e.g. global-margin"),
    )
    value = models.DecimalField(
        _("value"),
        max_digits=10,
        decimal_places=4,
    )
    last_updated = models.DateTimeField(
        _("last updated"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("pricing variable")
        verbose_name_plural = _("pricing variables")
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.name}: {self.value}"


class RawMaterial(TimeStampedModel):
    """Physical components like Paper, Vinyl, or PP Film."""

    class UnitMeasure(models.TextChoices):
        M2 = "m2", _("Square Meter")
        SHEET = "sheet", _("Sheet")

    material_type = models.CharField(
        _("material type"),
        max_length=100,
    )
    cost_per_unit = models.DecimalField(
        _("cost per unit"),
        max_digits=10,
        decimal_places=2,
    )
    unit_measure = models.CharField(
        _("unit measure"),
        max_length=20,
        choices=UnitMeasure.choices,
    )

    class Meta:
        verbose_name = _("raw material")
        verbose_name_plural = _("raw materials")
        ordering = ["material_type"]

    def __str__(self) -> str:
        return f"{self.material_type} ({self.get_unit_measure_display()})"

    def calculate_cost(self, quantity) -> Decimal:
        """Compute base material cost before margins."""
        return self.cost_per_unit * Decimal(str(quantity))


class FinishingOption(TimeStampedModel):
    """Additional processes like Lamination, Eyelets, or Stands."""

    process_name = models.CharField(
        _("process name"),
        max_length=100,
    )
    setup_fee = models.DecimalField(
        _("setup fee"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
    )
    unit_cost = models.DecimalField(
        _("unit cost"),
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        verbose_name = _("finishing option")
        verbose_name_plural = _("finishing options")
        ordering = ["process_name"]

    def __str__(self) -> str:
        return self.process_name

    def get_total_finishing_cost(self, quantity) -> Decimal:
        """Calculate total for this specific finishing process."""
        return self.setup_fee + (self.unit_cost * Decimal(str(quantity)))


class PricingEngine(TimeStampedModel):
    """
    Combines material + finishing + central margins for an instant quote.
    """

    product_name = models.CharField(
        _("product name"),
        max_length=255,
    )
    material = models.ForeignKey(
        RawMaterial,
        on_delete=models.PROTECT,
        related_name="pricing_engines",
    )
    finishes = models.ManyToManyField(
        FinishingOption,
        blank=True,
        related_name="pricing_engines",
        verbose_name=_("finishes"),
    )

    class Meta:
        verbose_name = _("pricing engine")
        verbose_name_plural = _("pricing engines")
        ordering = ["product_name"]

    def __str__(self) -> str:
        return self.product_name

    def generate_instant_quote(self, quantity: int, area_m2: float = 1) -> Decimal:
        """Combine material + finishing + central margins."""
        m_cost = self.material.calculate_cost(Decimal(str(area_m2 * quantity)))
        f_cost = sum(
            f.get_total_finishing_cost(quantity) for f in self.finishes.all()
        )
        try:
            margin_var = PricingVariable.objects.get(key="global-margin")
            margin = margin_var.value
        except PricingVariable.DoesNotExist:
            margin = Decimal("0")
        return (m_cost + f_cost) * (1 + margin)