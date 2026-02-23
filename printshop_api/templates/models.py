from decimal import Decimal
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from common.models import TimeStampedModel


class TemplateCategory(TimeStampedModel):
    """Category for print templates, e.g. Business Cards, Flyers."""

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="template_categories",
        null=True,
        blank=True,
        help_text=_("Shop that owns this category. Null = global/system category."),
    )
    name = models.CharField(
        _("name"),
        max_length=100,
        help_text=_("e.g., Business Cards, Flyers"),
    )
    slug = models.SlugField(
        _("slug"),
        max_length=100,
        help_text=_("Unique per shop (or globally when shop is null)."),
    )
    icon_svg_path = models.TextField(
        _("icon SVG path"),
        blank=True,
        help_text=_("Inline SVG path for the filter icon."),
    )
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Category description for customers"),
    )
    display_order = models.PositiveIntegerField(
        _("display order"),
        default=0,
        help_text=_("Order in which category appears in listings"),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
    )

    class Meta:
        verbose_name = _("template category")
        verbose_name_plural = _("template categories")
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(shop__isnull=True),
                name="unique_global_category_slug",
            ),
            models.UniqueConstraint(
                fields=["shop", "slug"],
                condition=models.Q(shop__isnull=False),
                name="unique_shop_category_slug",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PrintTemplate(TimeStampedModel):
    """
    A print product template for the gallery (e.g. Premium Business Cards).
    Customers can browse these and convert them into quote requests.
    """

    class PrintSides(models.TextChoices):
        SIMPLEX = "SIMPLEX", _("Single-sided")
        DUPLEX = "DUPLEX", _("Double-sided")

    title = models.CharField(
        _("title"),
        max_length=200,
        help_text=_("e.g., Premium Business Cards"),
    )
    slug = models.SlugField(
        _("slug"),
        max_length=200,
        blank=True,
        help_text=_("Unique per shop (or globally when shop is null)."),
    )
    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="print_templates",
        null=True,
        blank=True,
        help_text=_("Shop that owns this template. Null = global/system template."),
    )
    category = models.ForeignKey(
        TemplateCategory,
        on_delete=models.CASCADE,
        related_name="print_templates",
    )
    description = models.TextField(
        _("description"),
        blank=True,
        help_text=_("Detailed description for customers"),
    )
    
    # Pricing (base price for display, actual calculated on quote)
    base_price = models.DecimalField(
        _("starting price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Starting price for display (e.g., KES 1,200)"),
    )
    min_quantity = models.PositiveIntegerField(
        _("minimum quantity"),
        default=1,
        help_text=_("Minimum order quantity"),
    )
    min_gsm = models.PositiveIntegerField(
        _("minimum GSM"),
        null=True,
        blank=True,
        help_text=_("Minimum paper weight allowed (e.g., 130)"),
    )
    max_gsm = models.PositiveIntegerField(
        _("maximum GSM"),
        null=True,
        blank=True,
        help_text=_("Maximum paper weight allowed (e.g., 400)"),
    )

    # Product specifications (for quote conversion)
    final_width = models.DecimalField(
        _("width (mm)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Final product width in mm"),
    )
    final_height = models.DecimalField(
        _("height (mm)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Final product height in mm"),
    )
    default_gsm = models.PositiveIntegerField(
        _("default GSM"),
        null=True,
        blank=True,
        help_text=_("Default paper weight (e.g., 300)"),
    )
    default_print_sides = models.CharField(
        _("default print sides"),
        max_length=10,
        choices=PrintSides.choices,
        default=PrintSides.DUPLEX,
    )
    ups_per_sheet = models.PositiveIntegerField(
        _("units per sheet"),
        null=True,
        blank=True,
        help_text=_("Imposition: how many finished units fit on one sheet (N-Up). Used for sheets_needed calculation."),
    )

    # Display properties
    preview_image = models.ImageField(
        _("preview image"),
        upload_to="templates/previews/",
        blank=True,
    )
    dimensions_label = models.CharField(
        _("dimensions label"),
        max_length=50,
        help_text=_("e.g., 90 × 55 mm"),
    )
    weight_label = models.CharField(
        _("weight label"),
        max_length=50,
        help_text=_("e.g., 350gsm"),
    )
    
    # Badges/Flags
    is_popular = models.BooleanField(_("popular"), default=False)
    is_best_value = models.BooleanField(_("best value"), default=False)
    is_new = models.BooleanField(_("new"), default=False)
    is_active = models.BooleanField(_("active"), default=True)
    
    # SEO
    meta_description = models.CharField(
        _("meta description"),
        max_length=160,
        blank=True,
    )

    class Meta:
        verbose_name = _("print template")
        verbose_name_plural = _("print templates")
        ordering = ["category", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(shop__isnull=True),
                name="unique_global_template_slug",
            ),
            models.UniqueConstraint(
                fields=["shop", "slug"],
                condition=models.Q(shop__isnull=False),
                name="unique_shop_template_slug",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_starting_price_display(self) -> str:
        """Returns price formatted for the gallery grid."""
        return f"KES {self.base_price:,.0f}"

    def get_gallery_badges(self) -> list[str]:
        """Return list of badges like 'Popular' or 'Best Value'."""
        badges = []
        if self.is_popular:
            badges.append("Popular")
        if self.is_best_value:
            badges.append("Best Value")
        if self.is_new:
            badges.append("New")
        return badges


class TemplateFinishing(TimeStampedModel):
    """
    Finishing options available for a template.
    Links to shop's FinishingService for pricing; optional price_adjustment override.
    """
    
    template = models.ForeignKey(
        PrintTemplate,
        on_delete=models.CASCADE,
        related_name="finishing_options",
    )
    finishing_service = models.ForeignKey(
        "pricing.FinishingService",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="template_finishings",
        help_text=_("Shop finishing service for pricing. When null, use price_adjustment."),
    )
    name = models.CharField(
        _("finishing name"),
        max_length=100,
        help_text=_("e.g., Matt Lamination, Spot UV (fallback when finishing_service null)"),
    )
    description = models.TextField(
        _("description"),
        blank=True,
    )
    is_mandatory = models.BooleanField(
        _("mandatory"),
        default=False,
        help_text=_("If true, this finishing is always included"),
    )
    is_default = models.BooleanField(
        _("selected by default"),
        default=False,
        help_text=_("If true, this is pre-selected for optional finishing"),
    )
    price_adjustment = models.DecimalField(
        _("price adjustment"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Override per unit when finishing_service set; or sole price when null"),
    )
    display_order = models.PositiveIntegerField(
        _("display order"),
        default=0,
    )

    class Meta:
        verbose_name = _("template finishing")
        verbose_name_plural = _("template finishings")
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        mandatory = " (Mandatory)" if self.is_mandatory else ""
        label = self.finishing_service.name if self.finishing_service else self.name
        return f"{self.template.title} - {label}{mandatory}"


class TemplateOption(TimeStampedModel):
    """
    Configurable options for templates (e.g., paper types, sizes).
    Allows customers to customize their order.
    """
    
    class OptionType(models.TextChoices):
        PAPER_GSM = "PAPER_GSM", _("Paper Weight (GSM)")
        SIZE = "SIZE", _("Size")
        QUANTITY = "QUANTITY", _("Quantity")
        COLOR_MODE = "COLOR_MODE", _("Color Mode")
        OTHER = "OTHER", _("Other")

    template = models.ForeignKey(
        PrintTemplate,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_type = models.CharField(
        _("option type"),
        max_length=20,
        choices=OptionType.choices,
    )
    label = models.CharField(
        _("label"),
        max_length=100,
        help_text=_("Display label (e.g., '300 GSM', '500 pcs')"),
    )
    value = models.CharField(
        _("value"),
        max_length=100,
        help_text=_("Actual value for calculation"),
    )
    price_modifier = models.DecimalField(
        _("price modifier"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Price change when this option is selected"),
    )
    is_default = models.BooleanField(
        _("default"),
        default=False,
    )
    display_order = models.PositiveIntegerField(
        _("display order"),
        default=0,
    )

    class Meta:
        verbose_name = _("template option")
        verbose_name_plural = _("template options")
        ordering = ["option_type", "display_order"]

    def __str__(self) -> str:
        return f"{self.template.title} - {self.get_option_type_display()}: {self.label}"
