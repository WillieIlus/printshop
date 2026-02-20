# shops/models.py

import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

# Imported from the hypothetical common app as requested
from common.models import TimeStampedModel


class Shop(TimeStampedModel):
    """
    Represents a print shop or business entity.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_shops",
        help_text=_("The primary owner of the shop account.")
    )
    name = models.CharField(_("shop name"), max_length=255, db_index=True)
    slug = models.SlugField(_("slug"), max_length=255, unique=True)
    description = models.TextField(_("description"), blank=True)

    # Contact Details
    business_email = models.EmailField(_("business email"), help_text=_("Public contact email."))
    phone_number = models.CharField(_("phone number"), max_length=50, blank=True)

    # Physical Address
    address_line = models.CharField(_("address"), max_length=255)
    city = models.CharField(_("city"), max_length=100, db_index=True)
    state = models.CharField(_("state/province"), max_length=100, blank=True)
    zip_code = models.CharField(_("zip/postal code"), max_length=20)
    country = models.CharField(_("country"), max_length=100, default="USA")

    # GPS Location
    # Precision: 6 decimal places is ~11cm resolution, sufficient for mapping.
    latitude = models.DecimalField(
        _("latitude"), 
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True
    )
    longitude = models.DecimalField(
        _("longitude"), 
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True
    )

    # Status Flags
    is_verified = models.BooleanField(
        _("verified"), 
        default=False, 
        help_text=_("Designates whether this shop has been verified via claim.")
    )
    is_active = models.BooleanField(
        _("active"), 
        default=True, 
        help_text=_("Designates whether this shop is visible/active.")
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("shop")
        verbose_name_plural = _("shops")
        indexes = [
            models.Index(fields=["name", "city"]),
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self):
        return self.name


class ShopMember(TimeStampedModel):
    """
    Links users to shops with specific roles (Staff, Managers, etc.).
    """
    class Role(models.TextChoices):
        OWNER = "OWNER", _("Owner")
        MANAGER = "MANAGER", _("Manager")
        STAFF = "STAFF", _("Staff")
        DESIGNER = "DESIGNER", _("Designer")

    shop = models.ForeignKey(
        Shop, 
        on_delete=models.CASCADE, 
        related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="shop_memberships"
    )
    role = models.CharField(
        _("role"), 
        max_length=20, 
        choices=Role.choices, 
        default=Role.STAFF
    )
    is_active = models.BooleanField(
        _("active"), 
        default=True,
        help_text=_("Designates whether this user has active access to the shop.")
    )

    class Meta:
        verbose_name = _("shop member")
        verbose_name_plural = _("shop members")
        constraints = [
            # Ensure a user is not added to the same shop twice
            models.UniqueConstraint(
                fields=["shop", "user"], 
                name="unique_shop_membership"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.shop.name} ({self.get_role_display()})"


class OpeningHours(TimeStampedModel):
    """
    Weekly opening hours for a specific shop.
    """
    class Weekday(models.IntegerChoices):
        MONDAY = 1, _("Monday")
        TUESDAY = 2, _("Tuesday")
        WEDNESDAY = 3, _("Wednesday")
        THURSDAY = 4, _("Thursday")
        FRIDAY = 5, _("Friday")
        SATURDAY = 6, _("Saturday")
        SUNDAY = 7, _("Sunday")

    shop = models.ForeignKey(
        Shop, 
        on_delete=models.CASCADE, 
        related_name="opening_hours"
    )
    weekday = models.IntegerField(
        _("weekday"), 
        choices=Weekday.choices, 
        db_index=True
    )
    from_hour = models.TimeField(_("opening time"), null=True, blank=True)
    to_hour = models.TimeField(_("closing time"), null=True, blank=True)
    is_closed = models.BooleanField(_("closed"), default=False)

    class Meta:
        verbose_name = _("opening hour")
        verbose_name_plural = _("opening hours")
        ordering = ["weekday", "from_hour"]
        constraints = [
            # Prevent duplicate entries for the same day/start time for a shop
            models.UniqueConstraint(
                fields=["shop", "weekday", "from_hour"],
                name="unique_shop_daily_hours"
            )
        ]

    def clean(self):
        """
        Validate that closing time is after opening time if not closed.
        """
        super().clean()
        if not self.is_closed:
            if not self.from_hour or not self.to_hour:
                raise ValidationError(_("Opening and closing times are required if the shop is open."))
            if self.from_hour >= self.to_hour:
                raise ValidationError(_("Closing time must be after opening time."))

    def __str__(self):
        day = self.get_weekday_display()
        if self.is_closed:
            return f"{self.shop.name}: {day} (Closed)"
        return f"{self.shop.name}: {day} {self.from_hour} - {self.to_hour}"


class ShopSocialLink(TimeStampedModel):
    """
    Social media links specifically for the Shop entity.
    """
    class Platform(models.TextChoices):
        FACEBOOK = "facebook", _("Facebook")
        INSTAGRAM = "instagram", _("Instagram")
        TWITTER = "twitter", _("Twitter / X")
        LINKEDIN = "linkedin", _("LinkedIn")
        TIKTOK = "tiktok", _("TikTok")
        WEBSITE = "website", _("Official Website")
        OTHER = "other", _("Other")

    shop = models.ForeignKey(
        Shop, 
        on_delete=models.CASCADE, 
        related_name="social_links"
    )
    platform = models.CharField(
        _("platform"), 
        max_length=20, 
        choices=Platform.choices
    )
    url = models.URLField(_("URL"), max_length=500)
    username = models.CharField(
        _("username/handle"), 
        max_length=100, 
        blank=True, 
        help_text=_("Optional handle for display.")
    )

    class Meta:
        verbose_name = _("shop social link")
        verbose_name_plural = _("shop social links")
        constraints = [
            # One link per platform per shop
            models.UniqueConstraint(
                fields=["shop", "platform"], 
                name="unique_shop_social_platform"
            )
        ]

    def __str__(self):
        return f"{self.get_platform_display()} - {self.shop.name}"


class ShopClaim(TimeStampedModel):
    """
    Workflow model for users claiming ownership of a shop via email verification.
    """
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        VERIFIED = "VERIFIED", _("Verified / Approved")
        REJECTED = "REJECTED", _("Rejected")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shop_claims",
        help_text=_("The user submitting the claim.")
    )
    # Nullable because they might be claiming a shop that isn't in the DB yet (new listing)
    shop = models.ForeignKey(
        Shop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claims",
        help_text=_("The existing shop being claimed, if applicable.")
    )
    business_name = models.CharField(
        _("business name"), 
        max_length=255,
        help_text=_("Name of the business as stated in the claim.")
    )
    business_email = models.EmailField(
        _("business email"),
        help_text=_("The corporate email used for verification.")
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    token = models.UUIDField(
        _("verification token"),
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    admin_notes = models.TextField(
        _("admin notes"), 
        blank=True,
        help_text=_("Internal notes regarding this claim.")
    )

    class Meta:
        verbose_name = _("shop claim")
        verbose_name_plural = _("shop claims")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Claim by {self.user} for '{self.business_name}' ({self.get_status_display()})"


class ShopPaperCapability(TimeStampedModel):
    """
    Shop's paper capability per sheet size.
    Defines min/max GSM the shop can handle for each sheet size.
    Used together with template GSM constraints when calculating prices.
    """

    class SheetSize(models.TextChoices):
        A5 = "A5", _("A5")
        A4 = "A4", _("A4")
        A3 = "A3", _("A3")
        SRA3 = "SRA3", _("SRA3")

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="paper_capabilities",
    )
    sheet_size = models.CharField(
        _("sheet size"),
        max_length=20,
        choices=SheetSize.choices,
    )
    max_gsm = models.PositiveIntegerField(
        _("maximum GSM"),
        help_text=_("Maximum paper weight this shop can handle for this size"),
    )
    min_gsm = models.PositiveIntegerField(
        _("minimum GSM"),
        null=True,
        blank=True,
        help_text=_("Optional minimum paper weight"),
    )

    class Meta:
        verbose_name = _("shop paper capability")
        verbose_name_plural = _("shop paper capabilities")
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "sheet_size"],
                name="unique_shop_sheet_size_capability",
            ),
        ]

    def __str__(self):
        return f"{self.shop.name} - {self.sheet_size}: {self.min_gsm or 0}-{self.max_gsm}gsm"