# inventory/serializers.py

from rest_framework import serializers

from .models import Machine, Paper


# =============================================================================
# Machine Serializers
# =============================================================================

class MachinePublicSerializer(serializers.ModelSerializer):
    """Minimal serializer for public display."""
    type_display = serializers.CharField(source="get_machine_type_display", read_only=True)

    class Meta:
        model = Machine
        fields = ["id", "name", "machine_type", "type_display"]


class MachineSerializer(serializers.ModelSerializer):
    """Main serializer for Machines."""
    type_display = serializers.CharField(source="get_machine_type_display", read_only=True)

    class Meta:
        model = Machine
        fields = [
            "id",
            "name",
            "machine_type",
            "type_display",
            "max_paper_width",
            "max_paper_height",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        shop = self.context.get("shop")
        if not shop:
            return value
        qs = Machine.objects.filter(shop=shop, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A machine with this name already exists in your shop.")
        return value

    def create(self, validated_data):
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)


# =============================================================================
# Paper Serializers
# =============================================================================

class PaperSerializer(serializers.ModelSerializer):
    """Serializer for Paper (unified: buy/sell + optional stock)."""
    sheet_size_display = serializers.CharField(source="get_sheet_size_display", read_only=True)
    paper_type_display = serializers.CharField(source="get_paper_type_display", read_only=True)
    display_name = serializers.CharField(read_only=True)
    needs_reorder = serializers.BooleanField(read_only=True)

    class Meta:
        model = Paper
        fields = [
            "id",
            "sheet_size",
            "sheet_size_display",
            "gsm",
            "paper_type",
            "paper_type_display",
            "width_mm",
            "height_mm",
            "buying_price",
            "selling_price",
            "quantity_in_stock",
            "reorder_level",
            "is_active",
            "display_name",
            "needs_reorder",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "width_mm", "height_mm", "created_at", "updated_at"]

    def validate(self, attrs):
        shop = self.context.get("shop")
        if not shop:
            return attrs
        sheet_size = attrs.get("sheet_size", getattr(self.instance, "sheet_size", None))
        gsm = attrs.get("gsm", getattr(self.instance, "gsm", None))
        paper_type = attrs.get("paper_type", getattr(self.instance, "paper_type", None))
        qs = Paper.objects.filter(shop=shop, sheet_size=sheet_size, gsm=gsm, paper_type=paper_type)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A paper with this size, GSM and type already exists.")
        return attrs

    def create(self, validated_data):
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)
