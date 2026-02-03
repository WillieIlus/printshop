from __future__ import annotations

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model providing self-updating created_at and updated_at fields.

    All models requiring timestamp tracking should inherit from this class
    to ensure consistent timestamp handling across the application.
    """

    created_at = models.DateTimeField(
        "created at",
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        "updated at",
        auto_now=True,
    )

    class Meta:
        abstract = True


class Testimonial(TimeStampedModel):
    """
    Customer testimonial or review for display on the site.
    Non-superusers are allowed to add testimonials; other add actions require superuser.
    """

    author_name = models.CharField(
        "author name",
        max_length=150,
    )
    author_role = models.CharField(
        "author role / company",
        max_length=150,
        blank=True,
    )
    quote = models.TextField(
        "quote",
        help_text="The testimonial text.",
    )
    is_approved = models.BooleanField(
        "approved",
        default=False,
        help_text="Only approved testimonials are shown publicly.",
    )
    order = models.PositiveIntegerField(
        "display order",
        default=0,
        help_text="Lower numbers appear first.",
    )

    class Meta:
        verbose_name = "testimonial"
        verbose_name_plural = "testimonials"
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"{self.author_name}: {self.quote[:50]}…" if len(self.quote) > 50 else f"{self.author_name}: {self.quote}"