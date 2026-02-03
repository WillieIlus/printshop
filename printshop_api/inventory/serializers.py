# inventory/serializers.py

from django.db import transaction
from rest_framework import serializers

from .models import Machine, MachineCapability, Material, MaterialStock


# =============================================================================
# Machine Serializers
# =============================================================================

class MachineCapabilitySerializer(serializers.ModelSerializer):
    """
    Serializer for machine capabilities (nested in Machine).
    """
    feed_type_display = serializers.CharField(source="get_feed_type_display", read_only=True)

    class Meta:
        model = MachineCapability
        fields = [
            "id", 
            "feed_type", 
            "feed_type_display", 
            "max_width", 
            "max_height"
        ]
        read_only_fields = ["id"]
    
    def validate(self, attrs):
        """Cross-field validation for dimensions based on feed type."""
        feed_type = attrs.get("feed_type")
        max_width = attrs.get("max_width")
        max_height = attrs.get("max_height")
        
        # Note: If updating, self.instance might be needed to check existing values,
        # but for simplicity, we assume full payloads or handle partials carefully.
        
        if feed_type == MachineCapability.FeedType.SHEET_FED:
            if not max_width or not max_height:
                raise serializers.ValidationError("Sheet fed machines require both max width and max height.")
        
        if feed_type == MachineCapability.FeedType.ROLL_FED:
            if not max_width:
                raise serializers.ValidationError("Roll fed machines require a max width.")
                
        return attrs


class MachineSerializer(serializers.ModelSerializer):
    """
    Main serializer for Machines, including read-only capabilities.
    """
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    capabilities = MachineCapabilitySerializer(many=True, read_only=True)

    class Meta:
        model = Machine
        fields = [
            "id", 
            "name", 
            "type", 
            "type_display", 
            "is_active", 
            "capabilities", 
            "created_at", 
            "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        """Ensure name uniqueness per shop (context required)."""
        shop = self.context.get("shop")
        if not shop:
            return value # Skip if no context (shouldn't happen in viewset)
            
        qs = Machine.objects.filter(shop=shop, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise serializers.ValidationError("A machine with this name already exists in your shop.")
        return value

    def create(self, validated_data):
        """Inject shop from context."""
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)


class MachineWithCapabilitiesCreateSerializer(MachineSerializer):
    """
    Writable serializer that allows creating a machine AND its capabilities in one go.
    """
    capabilities = MachineCapabilitySerializer(many=True, required=False)

    def create(self, validated_data):
        capabilities_data = validated_data.pop("capabilities", [])
        validated_data["shop"] = self.context["shop"]
        
        with transaction.atomic():
            machine = Machine.objects.create(**validated_data)
            
            for cap_data in capabilities_data:
                MachineCapability.objects.create(machine=machine, **cap_data)
                
        return machine


# =============================================================================
# Material Serializers
# =============================================================================

class MaterialStockSerializer(serializers.ModelSerializer):
    """
    Serializer for specific material stock sizes.
    """
    class Meta:
        model = MaterialStock
        fields = [
            "id", 
            "label", 
            "width", 
            "height", 
            "current_stock_level",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        """Validate dimensions based on parent material type (requires nested context or lookup)."""
        # Note: Ideally validation happens in the View or Model.clean(), 
        # but we can do basic checks here if height is missing.
        return attrs


class MaterialSerializer(serializers.ModelSerializer):
    """
    Main serializer for Materials.
    """
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    unit_type_display = serializers.CharField(source="get_unit_type_display", read_only=True)
    stock_variants = MaterialStockSerializer(many=True, read_only=True)

    class Meta:
        model = Material
        fields = [
            "id", 
            "name", 
            "type", 
            "type_display", 
            "cost_per_unit", 
            "unit_type", 
            "unit_type_display", 
            "is_active", 
            "stock_variants",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        """Ensure name uniqueness per shop."""
        shop = self.context.get("shop")
        if not shop:
            return value
            
        qs = Material.objects.filter(shop=shop, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise serializers.ValidationError("A material with this name already exists.")
        return value

    def create(self, validated_data):
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)