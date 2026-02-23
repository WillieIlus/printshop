# quotes/serializers.py

from decimal import Decimal
from rest_framework import serializers

from .models import (
    ProductTemplate,
    Quote,
    QuoteItem,
    QuoteItemPart,
    QuoteItemFinishing,
)


# =============================================================================
# Product Template Serializers
# =============================================================================

class ProductTemplateSerializer(serializers.ModelSerializer):
    """Full serializer for shop product templates."""

    class Meta:
        model = ProductTemplate
        fields = [
            "id",
            "template",
            "name",
            "description",
            "defaults",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)


class ProductTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing."""

    class Meta:
        model = ProductTemplate
        fields = ["id", "name", "description", "is_active"]


# =============================================================================
# Quote Item Part Serializers
# =============================================================================

class QuoteItemPartSerializer(serializers.ModelSerializer):
    """Serializer for quote item parts."""
    
    paper_display = serializers.CharField(source="paper.display_name", read_only=True, allow_null=True)
    machine_name = serializers.CharField(source="machine.name", read_only=True, allow_null=True)
    print_sides_display = serializers.CharField(
        source="get_print_sides_display", 
        read_only=True
    )

    class Meta:
        model = QuoteItemPart
        fields = [
            "id",
            "name",
            "final_width",
            "final_height",
            "paper",
            "paper_display",
            "machine",
            "machine_name",
            "print_sides",
            "print_sides_display",
            "items_per_sheet",
            "total_sheets_required",
            "part_cost",
            "created_at",
        ]
        read_only_fields = [
            "id", 
            "items_per_sheet", 
            "total_sheets_required", 
            "part_cost",
            "created_at",
        ]


# =============================================================================
# Quote Item Finishing Serializers
# =============================================================================

class QuoteItemFinishingSerializer(serializers.ModelSerializer):
    """Serializer for quote item finishing."""
    
    finishing_name = serializers.CharField(
        source="finishing_service.name", 
        read_only=True
    )
    unit_price = serializers.DecimalField(
        source="finishing_service.selling_price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = QuoteItemFinishing
        fields = [
            "id",
            "finishing_service",
            "finishing_name",
            "unit_price",
            "calculated_cost",
            "created_at",
        ]
        read_only_fields = ["id", "calculated_cost", "created_at"]


# =============================================================================
# Quote Item Serializers
# =============================================================================

class QuoteItemSerializer(serializers.ModelSerializer):
    """Full serializer for quote items with nested parts and finishing."""
    
    parts = QuoteItemPartSerializer(many=True, read_only=True)
    finishing = QuoteItemFinishingSerializer(many=True, read_only=True)

    class Meta:
        model = QuoteItem
        fields = [
            "id",
            "name",
            "quantity",
            "calculated_price",
            "parts",
            "finishing",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "calculated_price", "created_at", "updated_at"]


class QuoteItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating quote items."""

    class Meta:
        model = QuoteItem
        fields = ["id", "name", "quantity"]
        read_only_fields = ["id"]


# =============================================================================
# Quote Serializers
# =============================================================================

class QuoteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing quotes."""
    
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    item_count = serializers.SerializerMethodField()
    source_template_title = serializers.CharField(
        source="source_template.title",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Quote
        fields = [
            "id",
            "reference",
            "title",
            "shop_name",
            "user_email",
            "status",
            "status_display",
            "source_template_title",
            "grand_total",
            "item_count",
            "valid_until",
            "created_at",
        ]

    def get_item_count(self, obj):
        return obj.items.count()


class QuoteDetailSerializer(serializers.ModelSerializer):
    """Full serializer for quote details."""
    
    shop_name = serializers.CharField(source="shop.name", read_only=True)
    shop_slug = serializers.CharField(source="shop.slug", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = QuoteItemSerializer(many=True, read_only=True)
    source_template_title = serializers.CharField(
        source="source_template.title",
        read_only=True,
        allow_null=True
    )
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Quote
        fields = [
            "id",
            "reference",
            "title",
            "shop",
            "shop_name",
            "shop_slug",
            "user",
            "user_email",
            "user_name",
            "source_template",
            "source_template_title",
            "status",
            "status_display",
            "customer_notes",
            "internal_notes",
            "valid_until",
            "is_expired",
            "net_total",
            "tax_rate",
            "tax_amount",
            "discount_amount",
            "grand_total",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reference",
            "net_total",
            "tax_amount",
            "grand_total",
            "created_at",
            "updated_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email


class QuoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating quotes."""

    class Meta:
        model = Quote
        fields = [
            "id",
            "reference",
            "title",
            "source_template",
            "customer_notes",
            "valid_until",
        ]
        read_only_fields = ["id", "reference"]

    def create(self, validated_data):
        validated_data["shop"] = self.context["shop"]
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class QuoteStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating quote status."""
    
    status = serializers.ChoiceField(choices=Quote.Status.choices)
    internal_notes = serializers.CharField(required=False, allow_blank=True)


# =============================================================================
# Customer Quote Request Serializer
# =============================================================================

class CustomerQuoteRequestSerializer(serializers.Serializer):
    """
    For customers requesting quotes without full authentication.
    Creates a minimal quote that shop can follow up on.
    """
    
    shop_id = serializers.IntegerField()
    product_name = serializers.CharField(max_length=200)
    quantity = serializers.IntegerField(min_value=1)
    
    # Contact info
    customer_name = serializers.CharField(max_length=100)
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    # Details
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    
    # Specifications (optional)
    width_mm = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True
    )
    height_mm = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False, 
        allow_null=True
    )
    paper_gsm = serializers.IntegerField(required=False, allow_null=True)
    print_sides = serializers.ChoiceField(
        choices=[("SIMPLEX", "Single-sided"), ("DUPLEX", "Double-sided")],
        required=False
    )
