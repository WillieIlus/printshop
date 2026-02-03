from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from common.models import TimeStampedModel


class TemplateCategory(TimeStampedModel):
    """Category for print templates, e.g. Business Cards, Flyers."""

    name = models.CharField(
        _("name"),
        max_length=100,
        help_text=_("e.g., Business Cards, Flyers"),
    )
    slug = models.SlugField(
        _("slug"),
        unique=True,
        max_length=100,
    )
    icon_svg_path = models.TextField(
        _("icon SVG path"),
        blank=True,
        help_text=_("Inline SVG path for the filter icon."),
    )

    class Meta:
        verbose_name = _("template category")
        verbose_name_plural = _("template categories")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PrintTemplate(TimeStampedModel):
    """A print product template for the gallery (e.g. Premium Business Cards)."""

    title = models.CharField(
        _("title"),
        max_length=200,
        help_text=_("e.g., Premium Business Cards"),
    )
    category = models.ForeignKey(
        TemplateCategory,
        on_delete=models.CASCADE,
        related_name="print_templates",
    )
    base_price = models.DecimalField(
        _("base price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("e.g., KES 1,200"),
    )
    preview_image = models.ImageField(
        _("preview image"),
        upload_to="templates/previews/",
        blank=True,
    )
    is_popular = models.BooleanField(
        _("popular"),
        default=False,
    )
    is_best_value = models.BooleanField(
        _("best value"),
        default=False,
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

    class Meta:
        verbose_name = _("print template")
        verbose_name_plural = _("print templates")
        ordering = ["category", "title"]

    def __str__(self) -> str:
        return self.title

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
        return badges
