# inventory/models.py

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import TimeStampedModel
from shops.models import Shop


class Machine(TimeStampedModel):
    """
    Represents physical hardware in the print shop.
    """
    class MachineType(models.TextChoices):
        DIGITAL_PRINTER = "DIGITAL_PRINTER", _("Digital Printer (Laser/Inkjet)")
        LARGE_FORMAT = "LARGE_FORMAT", _("Large Format Printer")
        PLOTTER = "PLOTTER", _("Plotter / Cutter")
        OFFSET = "OFFSET", _("Offset Press")
        FINISHING = "FINISHING", _("Finishing Equipment")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name="machines",
        help_text=_("The shop that owns this machine.")
    )
    name = models.CharField(
        _("machine name"),
        max_length=150,
        help_text=_("Internal identifier, e.g., 'Xerox Versant 80'.")
    )
    type = models.CharField(
        _("machine type"),
        max_length=30,
        choices=MachineType.choices,
        default=MachineType.DIGITAL_PRINTER
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("If false, this machine will not be available for new jobs.")
    )

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
        return f"{self.name} ({self.get_type_display()})"


class MachineCapability(TimeStampedModel):
    """
    Defines the physical constraints and handling capabilities of a machine.
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
        _("feed type"),
        max_length=20,
        choices=FeedType.choices,
        default=FeedType.SHEET_FED
    )
    max_width = models.DecimalField(
        _("max width (mm)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Maximum printable width in millimeters.")
    )
    max_height = models.DecimalField(
        _("max height (mm)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Maximum printable height (length) in millimeters. Leave blank for unlimited rolls.")
    )
    
    # Optional: Speed or capacity metrics could go here in future (e.g., sheets_per_hour)

    class Meta:
        verbose_name = _("machine capability")
        verbose_name_plural = _("machine capabilities")

    def clean(self):
        if self.feed_type == self.FeedType.SHEET_FED and (not self.max_width or not self.max_height):
            raise ValidationError(_("Sheet fed machines require both max width and max height."))
        if self.feed_type == self.FeedType.ROLL_FED and not self.max_width:
            raise ValidationError(_("Roll fed machines require a max width."))

    def __str__(self):
        return f"{self.machine.name} - {self.get_feed_type_display()}"


class Material(TimeStampedModel):
    """
    Represents the substrate/media definition.
    This defines the 'What' - e.g., 'Gloss Paper 150gsm'.
    """
    class MaterialType(models.TextChoices):
        SHEET = "SHEET", _("Sheet (Paper/Card)")
        ROLL = "ROLL", _("Roll (Vinyl/Banner/Canvas)")
        RIGID = "RIGID", _("Rigid (Foamex/Dibond/Acrylic)")

    class UnitType(models.TextChoices):
        PER_SHEET = "PER_SHEET", _("Per Sheet")
        PER_SQ_METER = "PER_SQ_METER", _("Per Square Meter")
        PER_LINEAR_METER = "PER_LINEAR_METER", _("Per Linear Meter")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name="materials",
        help_text=_("The shop that owns this material definition.")
    )
    name = models.CharField(
        _("material name"),
        max_length=150,
        help_text=_("e.g., 'Gloss Paper 300gsm'")
    )
    type = models.CharField(
        _("material type"),
        max_length=20,
        choices=MaterialType.choices,
        default=MaterialType.SHEET
    )
    cost_per_unit = models.DecimalField(
        _("cost per unit"),
        max_digits=14,
        decimal_places=4,
        help_text=_("The cost price the shop pays for this material based on the unit type.")
    )
    unit_type = models.CharField(
        _("cost unit"),
        max_length=20,
        choices=UnitType.choices,
        default=UnitType.PER_SHEET
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("If false, this material is unavailable for new calculations.")
    )

    class Meta:
        verbose_name = _("material")
        verbose_name_plural = _("materials")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "name"],
                name="unique_material_name_per_shop"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_unit_type_display()})"


class MaterialStock(TimeStampedModel):
    """
    Represents specific stock sizes/variants of a Material.
    Example: Material is 'Gloss 300gsm'. 
    Stocks might be: 'SRA3 Sheet', 'A4 Sheet', or '1.3m Wide Roll'.
    """
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="stock_variants"
    )
    label = models.CharField(
        _("label"),
        max_length=100,
        help_text=_("e.g., 'SRA3', '1370mm Roll', '4x8ft Sheet'")
    )
    width = models.DecimalField(
        _("width (mm)"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Width in millimeters.")
    )
    height = models.DecimalField(
        _("height (mm)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Height in millimeters. Leave empty for Rolls.")
    )
    current_stock_level = models.IntegerField(
        _("current stock"),
        default=0,
        help_text=_("Current quantity on hand (sheets or full rolls).")
    )

    class Meta:
        verbose_name = _("material stock")
        verbose_name_plural = _("material stocks")
        ordering = ["label"]

    def clean(self):
        # Validation to ensure sheets have height
        if self.material.type in [Material.MaterialType.SHEET, Material.MaterialType.RIGID] and not self.height:
            raise ValidationError(_("Sheet and Rigid materials must have a defined height."))

    def __str__(self):
        dim = f"{self.width}mm"
        if self.height:
            dim += f" x {self.height}mm"
        return f"{self.material.name} - {self.label} [{dim}]"