from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel


class UserManager(BaseUserManager["User"]):
    """
    Custom manager for User model where email is the unique identifier.

    Provides create_user and create_superuser methods that properly
    normalize email addresses and validate superuser flags.
    """

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields,
    ) -> User:
        """
        Create and save a regular user with the given email and password.

        Args:
            email: User's email address (will be normalized to lowercase domain)
            password: User's password (will be hashed)
            **extra_fields: Additional fields to set on the user

        Returns:
            The created User instance

        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError("The Email field must be set")

        # normalize_email lowercases the domain portion of the email
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields,
    ) -> User:
        """
        Create and save a superuser with the given email and password.

        Validates that is_staff and is_superuser are both True.

        Args:
            email: Superuser's email address
            password: Superuser's password
            **extra_fields: Additional fields to set on the user

        Returns:
            The created superuser instance

        Raises:
            ValueError: If is_staff or is_superuser is not True
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Custom User model using email as the primary authentication identifier.

    Design decisions:
    - AbstractBaseUser instead of AbstractUser: Full control over fields,
      no username field, email-only authentication.
    - PermissionsMixin: Adds groups, user_permissions fields and permission
      checking methods required by Django's auth framework.
    - TimeStampedModel inheritance: Automatic created_at/updated_at tracking.
    - Email normalization: Ensures consistent storage and lookup.
    """

    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        PRINTER = "PRINTER", "Printer"

    email = models.EmailField(
        "email address",
        unique=True,
        max_length=255,
        error_messages={
            "unique": "A user with that email already exists.",
        },
    )
    first_name = models.CharField(
        "first name",
        max_length=150,
        blank=True,
    )
    last_name = models.CharField(
        "last name",
        max_length=150,
        blank=True,
    )
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into the admin site.",
    )
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text=(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(
        "date joined",
        default=timezone.now,
    )
    email_verified = models.BooleanField(
        "email verified",
        default=False,
        help_text="Designates whether this user has verified their email via OTP.",
    )
    role = models.CharField(
        "role",
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )
    onboarding_completed = models.BooleanField(
        "onboarding completed",
        default=False,
        help_text="Designates whether the user has completed onboarding.",
    )

    objects = UserManager()

    # Email is the unique identifier for authentication
    USERNAME_FIELD = "email"
    # REQUIRED_FIELDS used by createsuperuser; email & password are implicit
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        """Return first_name plus last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self) -> str:
        """Return the short name for the user."""
        return self.first_name or self.email.split("@")[0]


class Profile(TimeStampedModel):
    """
    Extended user profile for additional, non-authentication user data.

    Design decisions:
    - Separation from User: Single Responsibility Principle - User handles
      authentication, Profile handles display/personal information.
    - OneToOneField: Each user has exactly one profile.
    - settings.AUTH_USER_MODEL: Decoupled reference supports swappable user models.
    - Dated avatar upload path: Prevents filename collisions and aids organization.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField(
        "biography",
        blank=True,
        max_length=500,
    )
    avatar = models.ImageField(
        "avatar",
        upload_to="avatars/%Y/%m/",
        blank=True,
    )
    website = models.URLField(
        "website",
        max_length=200,
        blank=True,
    )
    location = models.CharField(
        "location",
        max_length=100,
        blank=True,
    )
    birth_date = models.DateField(
        "birth date",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "profile"
        verbose_name_plural = "profiles"

    def __str__(self) -> str:
        return f"Profile of {self.user.email}"


class SocialLink(TimeStampedModel):
    """
    Social media links associated with a user profile.

    Design decisions:
    - Separate model vs. JSONField or per-platform fields:
      * Add/remove platforms without migrations (just update TextChoices)
      * Database-level uniqueness constraint per platform per profile
      * Proper queryability and validation
      * Clean relational data model
    - TextChoices for platform: Type-safe, IDE-friendly, human-readable labels.
    - ForeignKey to Profile: Keeps social data grouped with profile data.
    - Optional username field: Stores handle separately for display purposes.
    """

    class Platform(models.TextChoices):
        """
        Supported social media platforms.

        TextChoices provides:
        - Type safety and IDE autocompletion
        - Automatic form widget support
        - Human-readable display names via .label
        """

        TWITTER = "twitter", "Twitter / X"
        GITHUB = "github", "GitHub"
        LINKEDIN = "linkedin", "LinkedIn"
        FACEBOOK = "facebook", "Facebook"
        INSTAGRAM = "instagram", "Instagram"
        YOUTUBE = "youtube", "YouTube"
        TIKTOK = "tiktok", "TikTok"
        MASTODON = "mastodon", "Mastodon"
        BLUESKY = "bluesky", "Bluesky"
        THREADS = "threads", "Threads"
        DISCORD = "discord", "Discord"
        REDDIT = "reddit", "Reddit"
        TWITCH = "twitch", "Twitch"
        OTHER = "other", "Other"

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="social_links",
    )
    platform = models.CharField(
        "platform",
        max_length=20,
        choices=Platform.choices,
        db_index=True,
    )
    url = models.URLField(
        "URL",
        max_length=500,
    )
    username = models.CharField(
        "username / handle",
        max_length=100,
        blank=True,
        help_text="Optional username or handle on this platform",
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = "social link"
        verbose_name_plural = "social links"
        ordering = ["platform"]
        # Each profile can have at most one link per platform
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "platform"],
                name="unique_social_link_per_platform",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_platform_display()} - {self.profile.user.email}"


class EmailVerificationCode(TimeStampedModel):
    """
    OTP code for email verification.

    - Multiple codes can exist historically; only the latest active (unexpired, unused)
      matters for verification.
    - Code expires in 10 minutes.
    - used_at set on successful verification.
    - attempts incremented on failure; optionally lock after e.g. 10 tries.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_codes",
    )
    code = models.CharField("code", max_length=6)
    expires_at = models.DateTimeField("expires at")
    used_at = models.DateTimeField("used at", null=True, blank=True)
    attempts = models.PositiveIntegerField("attempts", default=0)

    class Meta:
        verbose_name = "email verification code"
        verbose_name_plural = "email verification codes"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Code for {self.user.email} (expires {self.expires_at})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_active(self) -> bool:
        return not self.is_expired and not self.is_used