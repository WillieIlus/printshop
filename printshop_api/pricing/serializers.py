# pricing/serializers.py
"""
Serializers for simplified pricing models.
"""

from rest_framework import serializers
from .models import (
    PrintingPrice,
    PaperPrice,
    MaterialPrice,
    FinishingService,
    VolumeDiscount,
    PriceCalculator,
    DefaultPrintingPriceTemplate,
    DefaultPaperPriceTemplate,
    DefaultMaterialPriceTemplate,
    DefaultFinishingServiceTemplate,
)


class PrintingPriceSerializer(serializers.ModelSerializer):
    """Printing prices per side."""
    
    profit_per_side = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = PrintingPrice
        fields = [
            "id", "machine", "sheet_size", "color_mode",
            "selling_price_per_side", "selling_price_duplex_per_sheet", "buying_price_per_side",
            "profit_per_side", "is_active", "is_default_seeded", "needs_review"
        ]
        read_only_fields = ["id", "profit_per_side"]


class PaperPriceSerializer(serializers.ModelSerializer):
    """Paper prices by GSM."""
    
    profit = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    margin_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = PaperPrice
        fields = [
            "id", "sheet_size", "gsm", "paper_type",
            "buying_price", "selling_price",
            "profit", "margin_percent", "is_active", "is_default_seeded", "needs_review"
        ]
        read_only_fields = ["id", "profit", "margin_percent"]


class MaterialPriceSerializer(serializers.ModelSerializer):
    """Material prices (SQM)."""
    
    profit = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = MaterialPrice
        fields = [
            "id", "material_type", "unit",
            "buying_price", "selling_price",
            "profit", "is_active", "is_default_seeded", "needs_review"
        ]
        read_only_fields = ["id", "profit"]


class FinishingServiceSerializer(serializers.ModelSerializer):
    """Finishing services."""
    
    profit = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = FinishingService
        fields = [
            "id", "name", "category", "charge_by",
            "buying_price", "selling_price",
            "profit", "is_default", "is_active", "is_default_seeded", "needs_review"
        ]
        read_only_fields = ["id", "profit"]


class VolumeDiscountSerializer(serializers.ModelSerializer):
    """Volume discounts."""
    
    class Meta:
        model = VolumeDiscount
        fields = [
            "id", "name", "min_quantity", "discount_percent", "is_active"
        ]
        read_only_fields = ["id"]


# =============================================================================
# DEFAULT TEMPLATES - Public read-only
# =============================================================================

class DefaultPrintingPriceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultPrintingPriceTemplate
        fields = [
            "id", "machine_category", "sheet_size", "color_mode",
            "selling_price_per_side", "selling_price_duplex_per_sheet"
        ]


class DefaultPaperPriceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultPaperPriceTemplate
        fields = ["id", "sheet_size", "paper_type", "gsm", "selling_price", "buying_price"]


class DefaultMaterialPriceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultMaterialPriceTemplate
        fields = ["id", "material_type", "unit", "selling_price", "buying_price"]


class DefaultFinishingServiceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultFinishingServiceTemplate
        fields = ["id", "name", "unit_type", "selling_price", "buying_price"]


# =============================================================================
# PUBLIC RATE CARD - What customers see
# =============================================================================

class PublicPrintingRateSerializer(serializers.Serializer):
    """Public printing rate for customers."""
    
    sheet_size = serializers.CharField()
    color_mode = serializers.CharField()
    price_per_side = serializers.DecimalField(max_digits=10, decimal_places=2)
    price_double_sided = serializers.DecimalField(max_digits=10, decimal_places=2)


class PublicPaperRateSerializer(serializers.Serializer):
    """Public paper rate for customers."""
    
    gsm = serializers.IntegerField()
    paper_type = serializers.CharField()
    price_per_sheet = serializers.DecimalField(max_digits=10, decimal_places=2)


class PublicFinishingRateSerializer(serializers.Serializer):
    """Public finishing rate for customers."""
    
    id = serializers.IntegerField()
    name = serializers.CharField()
    category = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    charge_by = serializers.CharField()
    is_default = serializers.BooleanField()


class RateCardSerializer(serializers.Serializer):
    """
    Complete rate card for customers.
    
    Shows:
    - Printing prices per side
    - Paper prices by GSM
    - Finishing services
    """
    
    printing = PublicPrintingRateSerializer(many=True)
    paper = PublicPaperRateSerializer(many=True)
    finishing = PublicFinishingRateSerializer(many=True)


# =============================================================================
# PRICE CALCULATOR
# =============================================================================

class PriceCalculatorInputSerializer(serializers.Serializer):
    """Input for price calculation."""
    
    sheet_size = serializers.ChoiceField(choices=["A5", "A4", "A3", "SRA3"])
    gsm = serializers.IntegerField(min_value=60, max_value=500)
    quantity = serializers.IntegerField(min_value=1)
    sides = serializers.IntegerField(min_value=1, max_value=2, default=1)
    paper_type = serializers.ChoiceField(
        choices=["GLOSS", "MATTE", "BOND", "ART"],
        default="GLOSS"
    )
    finishing_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[]
    )


class FinishingBreakdownSerializer(serializers.Serializer):
    """Breakdown of a finishing service cost."""
    
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    charge_by = serializers.CharField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)


class PriceCalculatorOutputSerializer(serializers.Serializer):
    """Output of price calculation."""
    
    quantity = serializers.IntegerField()
    sides = serializers.IntegerField()
    
    # Unit prices
    printing_price_per_side = serializers.DecimalField(max_digits=10, decimal_places=2)
    paper_price_per_sheet = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Totals
    total_printing = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_paper = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_finishing = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Finishing breakdown
    finishing_breakdown = FinishingBreakdownSerializer(many=True)
    
    # Grand totals
    grand_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    price_per_sheet = serializers.DecimalField(max_digits=10, decimal_places=2)
