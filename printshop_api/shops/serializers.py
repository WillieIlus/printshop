# shops/serializers.py

"""
Django REST Framework serializers for the shops app.

Includes serializers for:
- Shop CRUD operations
- Shop member/team management
- Opening hours management
- Shop social links
- Shop claim workflow
"""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from .models import OpeningHours, Shop, ShopClaim, ShopMember, ShopSocialLink

User = get_user_model()


# =============================================================================
# Nested/Helper Serializers
# =============================================================================


class ShopOwnerSerializer(serializers.ModelSerializer):
    """Read-only serializer for shop owner info."""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name"]
        read_only_fields = fields
    
    def get_full_name(self, obj) -> str:
        return obj.get_full_name() if hasattr(obj, "get_full_name") else f"{obj.first_name} {obj.last_name}".strip()


class ShopMemberUserSerializer(serializers.ModelSerializer):
    """Read-only serializer for member user info (minimal)."""
    
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = fields


# =============================================================================
# Opening Hours Serializers
# =============================================================================


class OpeningHoursSerializer(serializers.ModelSerializer):
    """Serializer for shop opening hours."""
    
    weekday_display = serializers.CharField(source="get_weekday_display", read_only=True)
    
    class Meta:
        model = OpeningHours
        fields = [
            "id",
            "weekday",
            "weekday_display",
            "from_hour",
            "to_hour",
            "is_closed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate that closing time is after opening time when not closed."""
        is_closed = attrs.get("is_closed", False)
        from_hour = attrs.get("from_hour")
        to_hour = attrs.get("to_hour")
        
        if not is_closed:
            if not from_hour or not to_hour:
                raise serializers.ValidationError(
                    "Opening and closing times are required if the shop is open."
                )
            if from_hour >= to_hour:
                raise serializers.ValidationError(
                    {"to_hour": "Closing time must be after opening time."}
                )
        
        return attrs


class OpeningHoursCreateSerializer(OpeningHoursSerializer):
    """Serializer for creating opening hours (shop set from context)."""
    
    class Meta(OpeningHoursSerializer.Meta):
        fields = OpeningHoursSerializer.Meta.fields + ["shop"]
        read_only_fields = ["id", "shop", "created_at", "updated_at"]
    
    def create(self, validated_data: dict[str, Any]) -> OpeningHours:
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)


class OpeningHoursBulkSerializer(serializers.Serializer):
    """Serializer for bulk updating opening hours for a shop."""
    
    hours = OpeningHoursSerializer(many=True)
    
    def validate_hours(self, value: list) -> list:
        """Validate no duplicate weekdays."""
        weekdays = [h.get("weekday") for h in value]
        if len(weekdays) != len(set(weekdays)):
            raise serializers.ValidationError("Duplicate weekday entries are not allowed.")
        return value
    
    def create(self, validated_data: dict[str, Any]) -> list[OpeningHours]:
        shop = self.context["shop"]
        hours_data = validated_data["hours"]
        
        with transaction.atomic():
            # Delete existing hours for this shop
            OpeningHours.objects.filter(shop=shop).delete()
            
            # Create new hours
            hours = [
                OpeningHours(shop=shop, **hour_data)
                for hour_data in hours_data
            ]
            return OpeningHours.objects.bulk_create(hours)


# =============================================================================
# Shop Social Link Serializers
# =============================================================================


class ShopSocialLinkSerializer(serializers.ModelSerializer):
    """Serializer for shop social links."""
    
    platform_display = serializers.CharField(source="get_platform_display", read_only=True)
    
    class Meta:
        model = ShopSocialLink
        fields = [
            "id",
            "platform",
            "platform_display",
            "url",
            "username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate unique platform per shop."""
        shop = self.context.get("shop")
        platform = attrs.get("platform")
        
        if shop and platform:
            existing = ShopSocialLink.objects.filter(shop=shop, platform=platform)
            
            # Exclude current instance if updating
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise serializers.ValidationError({
                    "platform": f"A social link for {platform} already exists for this shop."
                })
        
        return attrs


class ShopSocialLinkCreateSerializer(ShopSocialLinkSerializer):
    """Serializer for creating shop social links."""
    
    class Meta(ShopSocialLinkSerializer.Meta):
        fields = ShopSocialLinkSerializer.Meta.fields + ["shop"]
        read_only_fields = ["id", "shop", "created_at", "updated_at"]
    
    def create(self, validated_data: dict[str, Any]) -> ShopSocialLink:
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)


# =============================================================================
# Shop Member Serializers
# =============================================================================


class ShopMemberSerializer(serializers.ModelSerializer):
    """Serializer for shop members/team."""
    
    user = ShopMemberUserSerializer(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    
    class Meta:
        model = ShopMember
        fields = [
            "id",
            "user",
            "role",
            "role_display",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class ShopMemberCreateSerializer(serializers.ModelSerializer):
    """Serializer for adding a member to a shop."""
    
    user_email = serializers.EmailField(write_only=True)
    user = ShopMemberUserSerializer(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    
    class Meta:
        model = ShopMember
        fields = [
            "id",
            "user",
            "user_email",
            "role",
            "role_display",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]
    
    def validate_user_email(self, value: str) -> str:
        """Validate user exists."""
        try:
            User.objects.get(email=value.lower())
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address.")
        return value.lower()
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate user is not already a member and permission checks."""
        shop = self.context["shop"]
        request = self.context["request"]
        user_email = attrs.get("user_email")
        role = attrs.get("role", ShopMember.Role.STAFF)
        
        # Get the user to add
        user = User.objects.get(email=user_email)
        
        # Check if user is already a member
        if ShopMember.objects.filter(shop=shop, user=user).exists():
            raise serializers.ValidationError({
                "user_email": "This user is already a member of this shop."
            })
        
        # Check if non-owner is trying to add owner/manager
        if shop.owner != request.user:
            requester_membership = ShopMember.objects.filter(
                shop=shop, user=request.user, is_active=True
            ).first()
            
            if requester_membership and requester_membership.role == ShopMember.Role.MANAGER:
                if role in [ShopMember.Role.OWNER, ShopMember.Role.MANAGER]:
                    raise serializers.ValidationError({
                        "role": "Managers cannot add other managers or owners."
                    })
        
        attrs["user"] = user
        return attrs
    
    def create(self, validated_data: dict[str, Any]) -> ShopMember:
        validated_data.pop("user_email")
        user = validated_data.pop("user")
        shop = self.context["shop"]
        
        return ShopMember.objects.create(shop=shop, user=user, **validated_data)


class ShopMemberUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a shop member."""
    
    class Meta:
        model = ShopMember
        fields = ["role", "is_active"]
    
    def validate_role(self, value: str) -> str:
        """Prevent managers from promoting to manager/owner."""
        request = self.context["request"]
        shop = self.instance.shop
        
        if shop.owner != request.user:
            if value in [ShopMember.Role.OWNER, ShopMember.Role.MANAGER]:
                raise serializers.ValidationError(
                    "Only the shop owner can assign manager or owner roles."
                )
        
        return value


# =============================================================================
# Shop Serializers
# =============================================================================


class ShopListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for shop list views."""
    
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "slug",
            "city",
            "state",
            "country",
            "is_verified",
            "owner_name",
            "created_at",
        ]
        read_only_fields = fields
    
    def get_owner_name(self, obj) -> str:
        return obj.owner.get_full_name() if hasattr(obj.owner, "get_full_name") else obj.owner.email


class ShopDetailSerializer(serializers.ModelSerializer):
    """Full serializer for shop detail views with nested data."""
    
    owner = ShopOwnerSerializer(read_only=True)
    opening_hours = OpeningHoursSerializer(many=True, read_only=True)
    social_links = ShopSocialLinkSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Shop
        fields = [
            "id",
            "owner",
            "name",
            "slug",
            "description",
            "business_email",
            "phone_number",
            "address_line",
            "city",
            "state",
            "zip_code",
            "country",
            "latitude",
            "longitude",
            "is_verified",
            "is_active",
            "opening_hours",
            "social_links",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "owner", "slug", "is_verified", 
            "created_at", "updated_at"
        ]
    
    def get_member_count(self, obj) -> int:
        return obj.members.filter(is_active=True).count()


class ShopCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new shop."""
    
    class Meta:
        model = Shop
        fields = [
            "name",
            "slug",
            "description",
            "business_email",
            "phone_number",
            "address_line",
            "city",
            "state",
            "zip_code",
            "country",
            "latitude",
            "longitude",
        ]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }
    
    def validate_slug(self, value: str) -> str:
        """Validate slug is unique if provided."""
        if value and Shop.objects.filter(slug=value).exists():
            raise serializers.ValidationError("A shop with this slug already exists.")
        return value
    
    def create(self, validated_data: dict[str, Any]) -> Shop:
        """Create shop with current user as owner."""
        request = self.context["request"]
        
        # Auto-generate slug if not provided
        if not validated_data.get("slug"):
            base_slug = slugify(validated_data["name"])
            slug = base_slug
            counter = 1
            while Shop.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            validated_data["slug"] = slug
        
        # Set owner to current user
        validated_data["owner"] = request.user
        
        with transaction.atomic():
            shop = Shop.objects.create(**validated_data)
            
            # Add owner as a member with OWNER role
            ShopMember.objects.create(
                shop=shop,
                user=request.user,
                role=ShopMember.Role.OWNER,
                is_active=True,
            )
        
        return shop


class ShopUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a shop."""
    
    class Meta:
        model = Shop
        fields = [
            "name",
            "description",
            "business_email",
            "phone_number",
            "address_line",
            "city",
            "state",
            "zip_code",
            "country",
            "latitude",
            "longitude",
            "is_active",
        ]
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Only owner can deactivate shop."""
        request = self.context["request"]
        
        if "is_active" in attrs and attrs["is_active"] is False:
            if self.instance.owner != request.user:
                raise serializers.ValidationError({
                    "is_active": "Only the shop owner can deactivate the shop."
                })
        
        return attrs


class ShopTransferOwnershipSerializer(serializers.Serializer):
    """Serializer for transferring shop ownership."""
    
    new_owner_email = serializers.EmailField()
    
    def validate_new_owner_email(self, value: str) -> str:
        """Validate the new owner exists and is a member."""
        shop = self.context["shop"]
        
        try:
            new_owner = User.objects.get(email=value.lower())
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address.")
        
        # Check if new owner is a member of the shop
        if not ShopMember.objects.filter(shop=shop, user=new_owner, is_active=True).exists():
            raise serializers.ValidationError(
                "The new owner must be an active member of the shop."
            )
        
        self._new_owner = new_owner
        return value.lower()
    
    def save(self) -> Shop:
        """Transfer ownership."""
        shop = self.context["shop"]
        old_owner = shop.owner
        new_owner = self._new_owner
        
        with transaction.atomic():
            # Update shop owner
            shop.owner = new_owner
            shop.save(update_fields=["owner"])
            
            # Update old owner's membership to MANAGER
            ShopMember.objects.filter(shop=shop, user=old_owner).update(
                role=ShopMember.Role.MANAGER
            )
            
            # Update new owner's membership to OWNER
            ShopMember.objects.filter(shop=shop, user=new_owner).update(
                role=ShopMember.Role.OWNER
            )
        
        return shop


# =============================================================================
# Shop Claim Serializers
# =============================================================================


class ShopClaimListSerializer(serializers.ModelSerializer):
    """Serializer for listing claims."""
    
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    shop_name = serializers.CharField(source="shop.name", read_only=True, allow_null=True)
    
    class Meta:
        model = ShopClaim
        fields = [
            "id",
            "business_name",
            "business_email",
            "shop",
            "shop_name",
            "status",
            "status_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ShopClaimDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for claim views."""
    
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    shop_details = ShopListSerializer(source="shop", read_only=True, allow_null=True)
    
    class Meta:
        model = ShopClaim
        fields = [
            "id",
            "user",
            "user_email",
            "shop",
            "shop_details",
            "business_name",
            "business_email",
            "status",
            "status_display",
            "admin_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ShopClaimCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new shop claim."""
    
    class Meta:
        model = ShopClaim
        fields = [
            "id",
            "shop",
            "business_name",
            "business_email",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]
    
    def validate_shop(self, value: Shop | None) -> Shop | None:
        """Validate the shop is not already verified."""
        if value and value.is_verified:
            raise serializers.ValidationError(
                "This shop has already been verified and cannot be claimed."
            )
        return value
    
    def validate_business_email(self, value: str) -> str:
        """Normalize email."""
        return value.lower()
    
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Check for existing pending claims."""
        request = self.context["request"]
        shop = attrs.get("shop")
        
        # Check if user already has a pending claim for this shop
        existing_claim = ShopClaim.objects.filter(
            user=request.user,
            shop=shop,
            status=ShopClaim.Status.PENDING,
        )
        
        if existing_claim.exists():
            raise serializers.ValidationError(
                "You already have a pending claim for this shop."
            )
        
        return attrs
    
    def create(self, validated_data: dict[str, Any]) -> ShopClaim:
        """Create claim and send verification email."""
        request = self.context["request"]
        validated_data["user"] = request.user
        
        claim = ShopClaim.objects.create(**validated_data)
        
        # Send verification email
        self._send_verification_email(claim)
        
        return claim
    
    def _send_verification_email(self, claim: ShopClaim) -> None:
        """Send claim verification email."""
        frontend_url = getattr(settings, "SHOP_CLAIM_VERIFICATION_URL", "http://localhost:3000/shops/verify-claim")
        verification_url = f"{frontend_url}?token={claim.token}"
        
        send_mail(
            subject=f"Verify your claim for {claim.business_name}",
            message=f"""
Hello,

You have submitted a claim for the business "{claim.business_name}".

To verify your claim, please click the link below:

{verification_url}

If you did not submit this claim, please ignore this email.

Best regards,
The Print Shop Team
            """.strip(),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
            recipient_list=[claim.business_email],
            fail_silently=True,
        )


class ShopClaimVerifySerializer(serializers.Serializer):
    """Serializer for verifying a shop claim."""
    
    token = serializers.UUIDField()
    
    def validate_token(self, value: uuid.UUID) -> uuid.UUID:
        """Validate the token and get the claim."""
        try:
            claim = ShopClaim.objects.get(token=value, status=ShopClaim.Status.PENDING)
        except ShopClaim.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired verification token.")
        
        self._claim = claim
        return value
    
    def save(self) -> ShopClaim:
        """Verify the claim and activate the shop."""
        claim = self._claim
        
        with transaction.atomic():
            # Update claim status
            claim.status = ShopClaim.Status.VERIFIED
            claim.save(update_fields=["status"])
            
            if claim.shop:
                # Verify existing shop and transfer ownership
                shop = claim.shop
                shop.is_verified = True
                shop.owner = claim.user
                shop.save(update_fields=["is_verified", "owner"])
                
                # Add user as owner member if not already
                ShopMember.objects.get_or_create(
                    shop=shop,
                    user=claim.user,
                    defaults={
                        "role": ShopMember.Role.OWNER,
                        "is_active": True,
                    }
                )
            else:
                # Create new shop from claim
                base_slug = slugify(claim.business_name)
                slug = base_slug
                counter = 1
                while Shop.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                shop = Shop.objects.create(
                    owner=claim.user,
                    name=claim.business_name,
                    slug=slug,
                    business_email=claim.business_email,
                    is_verified=True,
                    is_active=True,
                    address_line="",
                    city="",
                    zip_code="",
                )
                
                # Add owner as member
                ShopMember.objects.create(
                    shop=shop,
                    user=claim.user,
                    role=ShopMember.Role.OWNER,
                    is_active=True,
                )
                
                # Link shop to claim
                claim.shop = shop
                claim.save(update_fields=["shop"])
        
        return claim


class ShopClaimAdminUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin to update claim status."""
    
    class Meta:
        model = ShopClaim
        fields = ["status", "admin_notes"]
    
    def validate_status(self, value: str) -> str:
        """Prevent changing from non-pending status."""
        if self.instance.status != ShopClaim.Status.PENDING:
            raise serializers.ValidationError(
                "Cannot modify a claim that is no longer pending."
            )
        return value