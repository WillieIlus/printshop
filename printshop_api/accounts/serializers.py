# accounts/serializers.py

"""
Django REST Framework serializers for authentication and user management.

Includes serializers for:
- User registration and email confirmation
- JWT authentication (login/logout)
- Password management (change/reset)
- Social authentication
- User, Profile, and SocialLink CRUD operations
"""

from __future__ import annotations

from typing import Any

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

# Import models - assumes they exist in the same app
from .models import Profile, SocialLink
from .services.verification import send_verification_code

User = get_user_model()


# =============================================================================
# JWT Token Serializers
# =============================================================================


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that uses email instead of username.
    
    Adds custom claims to the token payload including user email and name.
    """
    
    username_field = "email"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace 'username' with 'email' in the fields
        self.fields.pop("username", None)
        self.fields["email"] = serializers.EmailField()
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Map email to username_field for parent validation
        attrs["email"] = attrs.get("email", "").lower()
        data = super().validate(attrs)
        # Block login if email not verified
        if not self.user.email_verified:
            raise PermissionDenied(
                detail={"detail": "Email not verified", "code": "email_not_verified"},
            )
        return data
    
    @classmethod
    def get_token(cls, user: User) -> RefreshToken:
        """Add custom claims to the token."""
        token = super().get_token(user)

        # Add custom claims
        token["email"] = user.email
        token["first_name"] = user.first_name
        token["last_name"] = user.last_name
        token["role"] = user.role

        return token


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Serializer for token refresh response."""
    
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


# =============================================================================
# Registration & Email Confirmation Serializers
# =============================================================================


class RegisterSerializer(serializers.Serializer):
    """
    Serializer for user registration.
    
    Creates an inactive user and sends confirmation email.
    """
    
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    password_confirmation = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    
    def validate_email(self, value: str) -> str:
        """Ensure email is unique and normalized."""
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email
    
    def validate_password(self, value: str) -> str:
        """Validate password strength using Django's validators."""
        validate_password(value)
        return value
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Ensure passwords match."""
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError({
                "password_confirmation": "Passwords do not match."
            })
        return attrs
    
    def create(self, validated_data: dict[str, Any]) -> User:
        """Create inactive user and send confirmation email."""
        validated_data.pop("password_confirmation")
        
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            is_active=False,  # User must confirm email to activate
        )
        
        # Create profile for the user
        Profile.objects.create(user=user)
        
        # Send confirmation email
        self._send_confirmation_email(user)
        
        return user
    
    def _send_confirmation_email(self, user: User) -> None:
        """Generate token and send confirmation email."""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        confirmation_url = f"{settings.EMAIL_CONFIRMATION_URL}?uid={uid}&token={token}"
        
        send_mail(
            subject="Confirm your email address",
            message=f"""
Hello {user.first_name or 'there'},

Please confirm your email address by clicking the link below:

{confirmation_url}

If you didn't create an account, please ignore this email.

Best regards,
The Team
            """.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class RegisterResponseSerializer(serializers.Serializer):
    """Serializer for registration response (excludes password)."""
    
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)


# =============================================================================
# OTP Email Verification Serializers
# =============================================================================


class SignupSerializer(serializers.Serializer):
    """
    Serializer for signup with OTP verification.
    Creates user, sends verification code, returns { email, message }.
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    password_confirmation = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        """Ensure email is unique and normalized."""
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value: str) -> str:
        """Validate password strength using Django's validators."""
        validate_password(value)
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Ensure passwords match."""
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError({
                "password_confirmation": "Passwords do not match.",
            })
        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        """Create user (active, email_verified=False) and send OTP."""
        validated_data.pop("password_confirmation")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            is_active=True,
            email_verified=False,
        )
        Profile.objects.create(user=user)
        send_verification_code(user)
        return user


class EmailVerifySerializer(serializers.Serializer):
    """Serializer for email verification with OTP code."""

    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate code against latest unexpired unused code."""
        from django.utils import timezone

        from accounts.models import EmailVerificationCode

        email = attrs["email"].lower()
        code = attrs["code"].strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "No user found with this email."})

        # Get latest active (unexpired, unused) code
        verification = (
            EmailVerificationCode.objects.filter(
                user=user,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )

        if not verification:
            raise serializers.ValidationError(
                {"code": "No valid verification code found. Please request a new one."}
            )

        if verification.attempts >= 10:
            raise serializers.ValidationError(
                {"code": "Too many failed attempts. Please request a new code."}
            )

        if verification.code != code:
            verification.attempts += 1
            verification.save(update_fields=["attempts"])
            raise serializers.ValidationError({"code": "Invalid verification code."})

        attrs["user"] = user
        attrs["verification"] = verification
        return attrs

    def save(self) -> User:
        """Mark user as verified and code as used."""
        from django.utils import timezone

        user = self.validated_data["user"]
        verification = self.validated_data["verification"]

        user.email_verified = True
        user.save(update_fields=["email_verified"])

        verification.used_at = timezone.now()
        verification.save(update_fields=["used_at"])

        return user


class ResendCodeSerializer(serializers.Serializer):
    """Serializer for resending verification code. Rate limited (e.g. 3/min)."""

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        """Normalize email."""
        return value.lower()

    def save(self) -> User | None:
        """Generate new code and send email if user exists. Returns user or None."""
        email = self.validated_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        send_verification_code(user)
        return user


class EmailConfirmationSerializer(serializers.Serializer):
    """Serializer for email confirmation."""
    
    uid = serializers.CharField()
    token = serializers.CharField()
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate UID and token."""
        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"uid": "Invalid user ID."})
        
        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "Invalid or expired token."})
        
        attrs["user"] = user
        return attrs
    
    def save(self) -> User:
        """Activate the user."""
        user = self.validated_data["user"]
        user.is_active = True
        user.save(update_fields=["is_active"])
        return user


# =============================================================================
# Password Management Serializers
# =============================================================================


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for authenticated password change."""
    
    old_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    new_password_confirmation = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    
    def validate_old_password(self, value: str) -> str:
        """Verify the old password is correct."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
    
    def validate_new_password(self, value: str) -> str:
        """Validate new password strength."""
        validate_password(value, user=self.context["request"].user)
        return value
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Ensure new passwords match."""
        if attrs["new_password"] != attrs["new_password_confirmation"]:
            raise serializers.ValidationError({
                "new_password_confirmation": "New passwords do not match."
            })
        return attrs
    
    def save(self) -> User:
        """Update the user's password."""
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request.
    
    Sends reset email but doesn't reveal if email exists (security).
    """
    
    email = serializers.EmailField()
    
    def validate_email(self, value: str) -> str:
        """Normalize email."""
        return value.lower()
    
    def save(self) -> None:
        """Send password reset email if user exists."""
        email = self.validated_data["email"]
        
        try:
            user = User.objects.get(email=email, is_active=True)
            self._send_reset_email(user)
        except User.DoesNotExist:
            # Don't reveal that the user doesn't exist
            pass
    
    def _send_reset_email(self, user: User) -> None:
        """Generate token and send reset email."""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        reset_url = f"{settings.PASSWORD_RESET_URL}?uid={uid}&token={token}"
        
        send_mail(
            subject="Reset your password",
            message=f"""
Hello {user.first_name or 'there'},

You requested a password reset. Click the link below to set a new password:

{reset_url}

If you didn't request this, please ignore this email. The link will expire.

Best regards,
The Team
            """.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""
    
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    new_password_confirmation = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate UID, token, and password match."""
        # Validate UID
        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"uid": "Invalid user ID."})
        
        # Validate token
        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "Invalid or expired token."})
        
        # Validate passwords match
        if attrs["new_password"] != attrs["new_password_confirmation"]:
            raise serializers.ValidationError({
                "new_password_confirmation": "Passwords do not match."
            })
        
        # Validate password strength
        validate_password(attrs["new_password"], user=user)
        
        attrs["user"] = user
        return attrs
    
    def save(self) -> User:
        """Set the new password."""
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


# =============================================================================
# Logout Serializer
# =============================================================================


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout - blacklists the refresh token."""
    
    refresh = serializers.CharField()
    
    def validate_refresh(self, value: str) -> str:
        """Store the refresh token for blacklisting."""
        self.token = value
        return value
    
    def save(self) -> None:
        """Blacklist the refresh token."""
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except Exception as e:
            raise serializers.ValidationError({"refresh": "Invalid or expired token."})


# =============================================================================
# Social Authentication Serializers
# =============================================================================


class SocialLoginSerializer(serializers.Serializer):
    """
    Base serializer for social login.
    
    Accepts access token from frontend, validates with provider,
    creates/retrieves user, and returns JWT tokens.
    """
    
    access_token = serializers.CharField()
    
    # To be set by subclasses
    provider = None
    user_info_url = None
    
    def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Fetch user info from the social provider. Override in subclasses."""
        raise NotImplementedError
    
    def validate_access_token(self, value: str) -> str:
        """Validate and fetch user info from provider."""
        user_info = self.get_user_info(value)
        
        if not user_info or not user_info.get("email"):
            raise serializers.ValidationError("Failed to retrieve user info from provider.")
        
        self.user_info = user_info
        return value
    
    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        """Create or get user and return tokens."""
        email = self.user_info["email"].lower()
        
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": self.user_info.get("first_name", ""),
                "last_name": self.user_info.get("last_name", ""),
                "is_active": True,
                "email_verified": True,  # Provider-verified email
            }
        )
        
        # Create profile if user was just created
        if created:
            Profile.objects.create(user=user)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return {
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class GoogleLoginSerializer(SocialLoginSerializer):
    """Serializer for Google OAuth login."""
    
    provider = "google"
    
    def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Fetch user info from Google."""
        response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        
        if response.status_code != 200:
            raise serializers.ValidationError("Invalid Google access token.")
        
        data = response.json()
        
        return {
            "email": data.get("email"),
            "first_name": data.get("given_name", ""),
            "last_name": data.get("family_name", ""),
            "picture": data.get("picture"),
        }


class GitHubLoginSerializer(SocialLoginSerializer):
    """Serializer for GitHub OAuth login."""
    
    provider = "github"
    
    def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Fetch user info from GitHub."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        
        # Get user profile
        user_response = requests.get(
            "https://api.github.com/user",
            headers=headers,
            timeout=10,
        )
        
        if user_response.status_code != 200:
            raise serializers.ValidationError("Invalid GitHub access token.")
        
        user_data = user_response.json()
        
        # GitHub may not return email in user endpoint, need to fetch separately
        email = user_data.get("email")
        
        if not email:
            email_response = requests.get(
                "https://api.github.com/user/emails",
                headers=headers,
                timeout=10,
            )
            
            if email_response.status_code == 200:
                emails = email_response.json()
                primary_email = next(
                    (e for e in emails if e.get("primary") and e.get("verified")),
                    None
                )
                if primary_email:
                    email = primary_email["email"]
        
        # Parse name
        name = user_data.get("name", "") or ""
        name_parts = name.split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        return {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "avatar_url": user_data.get("avatar_url"),
        }


class SocialLoginResponseSerializer(serializers.Serializer):
    """Response serializer for social login."""
    
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.SerializerMethodField()
    
    def get_user(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Return basic user info."""
        user = obj["user"]
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }


# =============================================================================
# User Serializers
# =============================================================================


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.

    Exposes safe fields only - never exposes password.
    Supports role update (CUSTOMER <-> PRINTER) via PATCH /api/users/me/.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "email_verified",
            "role",
            "onboarding_completed",
        ]
        read_only_fields = ["id", "email", "is_active", "date_joined", "email_verified"]

    def validate_role(self, value: str) -> str:
        """Validate role is one of allowed choices."""
        if value not in [User.Role.CUSTOMER, User.Role.PRINTER]:
            raise serializers.ValidationError(
                f"Role must be {User.Role.CUSTOMER} or {User.Role.PRINTER}."
            )
        return value


class UserDetailSerializer(UserSerializer):
    """Extended user serializer with profile info for detail views."""
    
    profile_id = serializers.IntegerField(source="profile.id", read_only=True)
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["profile_id"]


# =============================================================================
# Profile Serializers
# =============================================================================


class SocialLinkNestedSerializer(serializers.ModelSerializer):
    """Read-only nested serializer for social links in profile."""
    
    platform_display = serializers.CharField(
        source="get_platform_display",
        read_only=True,
    )
    
    class Meta:
        model = SocialLink
        fields = [
            "id",
            "platform",
            "platform_display",
            "url",
            "username",
        ]
        read_only_fields = fields


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for Profile model.
    
    Includes nested read-only social links.
    """
    
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(
        source="user.get_full_name",
        read_only=True,
    )
    social_links = SocialLinkNestedSerializer(many=True, read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "user_email",
            "user_full_name",
            "bio",
            "avatar",
            "website",
            "location",
            "birth_date",
            "social_links",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "user_email", "user_full_name", "created_at", "updated_at"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating profile (excludes read-only nested fields)."""
    
    class Meta:
        model = Profile
        fields = [
            "bio",
            "avatar",
            "website",
            "location",
            "birth_date",
        ]


# =============================================================================
# SocialLink Serializers
# =============================================================================


class SocialLinkSerializer(serializers.ModelSerializer):
    """Serializer for SocialLink model."""
    
    platform_display = serializers.CharField(
        source="get_platform_display",
        read_only=True,
    )
    
    class Meta:
        model = SocialLink
        fields = [
            "id",
            "profile",
            "platform",
            "platform_display",
            "url",
            "username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "profile", "created_at", "updated_at"]
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate unique constraint for platform per profile."""
        request = self.context.get("request")
        profile = self.context.get("profile")
        platform = attrs.get("platform")
        
        if profile and platform:
            existing = SocialLink.objects.filter(
                profile=profile,
                platform=platform,
            )
            
            # Exclude current instance if updating
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise serializers.ValidationError({
                    "platform": f"A social link for {platform} already exists for this profile."
                })
        
        return attrs


class SocialLinkCreateSerializer(SocialLinkSerializer):
    """Serializer for creating social links (profile set from context)."""
    
    class Meta(SocialLinkSerializer.Meta):
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def create(self, validated_data: dict[str, Any]) -> SocialLink:
        """Set profile from context."""
        validated_data["profile"] = self.context["profile"]
        return super().create(validated_data)