# pricing/serializers.py

from decimal import Decimal
from rest_framework import serializers

from inventory.models import Machine, Material
from inventory.serializers import MachineSerializer, MaterialSerializer

from .models import (
    DigitalPrintPrice,
    MaterialPrice,
    FinishingPrice,
    PaperGSMPrice,
    VolumeDiscount,
)


# =============================================================================
# Digital Print Price Serializers
# =============================================================================

class DigitalPrintPriceSerializer(serializers.ModelSerializer):
    """Full serializer for DigitalPrintPrice with computed fields."""
    
    sheet_size_display = serializers.CharField(source="get_sheet_size_display", read_only=True)
    color_mode_display = serializers.CharField(source="get_color_mode_display", read_only=True)
    machine_name = serializers.CharField(source="machine.name", read_only=True)
    effective_duplex_rate = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = DigitalPrintPrice
        fields = [
            "id",
            "machine",
            "machine_name",
            "sheet_size",
            "sheet_size_display",
            "color_mode",
            "color_mode_display",
            "click_rate",
            "duplex_rate",
            "effective_duplex_rate",
            "minimum_order_quantity",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        """Ensure machine belongs to the same shop."""
        shop = self.context.get("shop")
        machine = attrs.get("machine") or (self.instance.machine if self.instance else None)
        
        if shop and machine and machine.shop_id != shop.id:
            raise serializers.ValidationError({
                "machine": "Selected machine does not belong to your shop."
            })
        
        return attrs

    def create(self, validated_data):
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)


class DigitalPrintPriceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing."""
    
    sheet_size_display = serializers.CharField(source="get_sheet_size_display", read_only=True)
    color_mode_display = serializers.CharField(source="get_color_mode_display", read_only=True)
    machine_name = serializers.CharField(source="machine.name", read_only=True)

    class Meta:
        model = DigitalPrintPrice
        fields = [
            "id",
            "machine_name",
            "sheet_size",
            "sheet_size_display",
            "color_mode",
            "color_mode_display",
            "click_rate",
            "is_active",
        ]


# =============================================================================
# Material Price Serializers
# =============================================================================

class MaterialPriceSerializer(serializers.ModelSerializer):
    """Full serializer for MaterialPrice with computed fields."""
    
    pricing_method_display = serializers.CharField(source="get_pricing_method_display", read_only=True)
    material_name = serializers.CharField(source="material.name", read_only=True)
    material_cost = serializers.DecimalField(
        source="material.cost_per_unit", 
        max_digits=14, 
        decimal_places=4, 
        read_only=True
    )
    material_unit_type = serializers.CharField(source="material.get_unit_type_display", read_only=True)
    calculated_selling_price = serializers.DecimalField(
        max_digits=14, decimal_places=4, read_only=True
    )
    profit_per_unit = serializers.DecimalField(
        max_digits=14, decimal_places=4, read_only=True
    )
    effective_margin_percentage = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True
    )

    class Meta:
        model = MaterialPrice
        fields = [
            "id",
            "material",
            "material_name",
            "material_cost",
            "material_unit_type",
            "pricing_method",
            "pricing_method_display",
            "selling_price_per_unit",
            "markup_percentage",
            "margin_percentage",
            "calculated_selling_price",
            "profit_per_unit",
            "effective_margin_percentage",
            "minimum_order_value",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        """Validate pricing method requirements and shop ownership."""
        shop = self.context.get("shop")
        material = attrs.get("material") or (self.instance.material if self.instance else None)
        
        if shop and material and material.shop_id != shop.id:
            raise serializers.ValidationError({
                "material": "Selected material does not belong to your shop."
            })
        
        pricing_method = attrs.get("pricing_method", 
            self.instance.pricing_method if self.instance else MaterialPrice.PricingMethod.FIXED
        )
        
        if pricing_method == MaterialPrice.PricingMethod.FIXED:
            if not attrs.get("selling_price_per_unit") and not (self.instance and self.instance.selling_price_per_unit):
                raise serializers.ValidationError({
                    "selling_price_per_unit": "Required when using fixed pricing method."
                })
        
        elif pricing_method == MaterialPrice.PricingMethod.MARKUP:
            if attrs.get("markup_percentage") is None and not (self.instance and self.instance.markup_percentage is not None):
                raise serializers.ValidationError({
                    "markup_percentage": "Required when using markup pricing method."
                })
        
        elif pricing_method == MaterialPrice.PricingMethod.MARGIN:
            if attrs.get("margin_percentage") is None and not (self.instance and self.instance.margin_percentage is not None):
                raise serializers.ValidationError({
                    "margin_percentage": "Required when using margin pricing method."
                })
        
        return attrs

    def create(self, validated_data):
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)


class MaterialPriceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing."""
    
    material_name = serializers.CharField(source="material.name", read_only=True)
    calculated_selling_price = serializers.DecimalField(
        max_digits=14, decimal_places=4, read_only=True
    )

    class Meta:
        model = MaterialPrice
        fields = [
            "id",
            "material_name",
            "calculated_selling_price",
            "is_active",
        ]


# =============================================================================
# Finishing Price Serializers
# =============================================================================

class FinishingPriceSerializer(serializers.ModelSerializer):
    """Full serializer for FinishingPrice."""
    
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    unit_display = serializers.CharField(source="get_unit_display", read_only=True)

    class Meta:
        model = FinishingPrice
        fields = [
            "id",
            "category",
            "category_display",
            "process_name",
            "description",
            "price",
            "unit",
            "unit_display",
            "setup_fee",
            "minimum_order_quantity",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)


class FinishingPriceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing."""
    
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    unit_display = serializers.CharField(source="get_unit_display", read_only=True)

    class Meta:
        model = FinishingPrice
        fields = [
            "id",
            "category_display",
            "process_name",
            "price",
            "unit_display",
            "is_active",
        ]


# =============================================================================
# Volume Discount Serializers
# =============================================================================

class VolumeDiscountSerializer(serializers.ModelSerializer):
    """Serializer for volume discounts."""
    
    discount_type_display = serializers.CharField(source="get_discount_type_display", read_only=True)

    class Meta:
        model = VolumeDiscount
        fields = [
            "id",
            "name",
            "minimum_quantity",
            "maximum_quantity",
            "discount_type",
            "discount_type_display",
            "discount_value",
            "applies_to_print",
            "applies_to_material",
            "applies_to_finishing",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)


# =============================================================================
# Rate Card Serializers (Composite Views)
# =============================================================================

class MachinePriceCardSerializer(serializers.Serializer):
    """
    Combines a Machine with all its associated DigitalPrintPrices.
    Used in the Rate Card endpoint.
    """
    
    machine_id = serializers.IntegerField(source="id")
    machine_name = serializers.CharField(source="name")
    machine_type = serializers.CharField(source="get_type_display")
    is_active = serializers.BooleanField()
    
    prices = serializers.SerializerMethodField()
    price_summary = serializers.SerializerMethodField()

    def get_prices(self, machine):
        """Get all print prices for this machine, grouped by sheet size."""
        shop = self.context.get("shop")
        prices = DigitalPrintPrice.objects.filter(
            machine=machine,
            shop=shop,
            is_active=True
        ).order_by("sheet_size", "color_mode")
        
        return DigitalPrintPriceListSerializer(prices, many=True).data

    def get_price_summary(self, machine):
        """
        Generate a quick summary showing min/max prices.
        Useful for quick reference.
        """
        shop = self.context.get("shop")
        prices = DigitalPrintPrice.objects.filter(
            machine=machine,
            shop=shop,
            is_active=True
        )
        
        if not prices.exists():
            return None
        
        rates = [p.click_rate for p in prices]
        return {
            "total_configurations": prices.count(),
            "min_click_rate": min(rates),
            "max_click_rate": max(rates),
            "avg_click_rate": sum(rates) / len(rates),
        }


class MaterialPriceCardSerializer(serializers.Serializer):
    """
    Combines a Material with its pricing and stock info.
    Used in the Rate Card endpoint.
    """
    
    material_id = serializers.IntegerField(source="id")
    material_name = serializers.CharField(source="name")
    material_type = serializers.CharField(source="get_type_display")
    cost_per_unit = serializers.DecimalField(max_digits=14, decimal_places=4)
    unit_type = serializers.CharField(source="get_unit_type_display")
    is_active = serializers.BooleanField()
    
    pricing = serializers.SerializerMethodField()
    available_sizes = serializers.SerializerMethodField()

    def get_pricing(self, material):
        """Get selling price configuration for this material."""
        shop = self.context.get("shop")
        
        try:
            price = MaterialPrice.objects.get(material=material, shop=shop)
            return {
                "pricing_method": price.get_pricing_method_display(),
                "selling_price": str(price.calculated_selling_price),
                "profit_per_unit": str(price.profit_per_unit),
                "margin_percentage": str(price.effective_margin_percentage),
                "is_active": price.is_active,
            }
        except MaterialPrice.DoesNotExist:
            return None

    def get_available_sizes(self, material):
        """List available stock sizes for this material."""
        stocks = material.stock_variants.filter(current_stock_level__gt=0)
        return [
            {
                "label": s.label,
                "dimensions": f"{s.width}mm x {s.height}mm" if s.height else f"{s.width}mm (roll)",
                "stock_level": s.current_stock_level,
            }
            for s in stocks
        ]


class FullRateCardSerializer(serializers.Serializer):
    """
    Complete Rate Card showing all pricing for a shop.
    This is the main endpoint response for /rate-card/.
    """
    
    shop_name = serializers.CharField()
    shop_slug = serializers.CharField()
    generated_at = serializers.DateTimeField()
    
    machines = MachinePriceCardSerializer(many=True)
    materials = MaterialPriceCardSerializer(many=True)
    finishing_services = FinishingPriceListSerializer(many=True)
    volume_discounts = VolumeDiscountSerializer(many=True)
    
    summary = serializers.SerializerMethodField()

    def get_summary(self, data):
        """Generate summary statistics for the rate card."""
        return {
            "total_machines": len(data.get("machines", [])),
            "total_materials": len(data.get("materials", [])),
            "total_finishing_services": len(data.get("finishing_services", [])),
            "total_volume_discounts": len(data.get("volume_discounts", [])),
        }


# =============================================================================
# Cost Calculator Serializers
# =============================================================================

class PrintCostCalculatorSerializer(serializers.Serializer):
    """
    Input serializer for calculating print job costs.
    """
    
    machine_id = serializers.IntegerField()
    sheet_size = serializers.ChoiceField(choices=DigitalPrintPrice.SheetSize.choices)
    color_mode = serializers.ChoiceField(choices=DigitalPrintPrice.ColorMode.choices)
    quantity = serializers.IntegerField(min_value=1)
    duplex = serializers.BooleanField(default=False)
    material_id = serializers.IntegerField(required=False, allow_null=True)
    finishing_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )


class PrintCostResultSerializer(serializers.Serializer):
    """
    Output serializer for print cost calculation results.
    """
    
    print_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    material_cost = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    finishing_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    total = serializers.DecimalField(max_digits=14, decimal_places=2)
    
    breakdown = serializers.DictField()


# =============================================================================
# Simple/Customer-Friendly Paper GSM Price Serializers
# =============================================================================

class PaperGSMPriceSerializer(serializers.ModelSerializer):
    """
    Full serializer for PaperGSMPrice - the simple pricing model.
    """
    
    sheet_size_display = serializers.CharField(source="get_sheet_size_display", read_only=True)
    profit_per_sheet = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    margin_percentage = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = PaperGSMPrice
        fields = [
            "id",
            "sheet_size",
            "sheet_size_display",
            "gsm",
            "paper_type",
            "price_per_sheet",
            "cost_per_sheet",
            "profit_per_sheet",
            "margin_percentage",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["shop"] = self.context["shop"]
        return super().create(validated_data)


class PaperGSMPriceListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing paper GSM prices.
    Designed for customer-facing rate cards.
    """
    
    class Meta:
        model = PaperGSMPrice
        fields = [
            "gsm",
            "paper_type",
            "price_per_sheet",
        ]


class SimpleRateCardPrintPriceSerializer(serializers.Serializer):
    """
    Simple print price display for customers.
    Shows: "A3 Color = KES 15 per side, KES 25 double-sided"
    """
    
    sheet_size = serializers.CharField()
    sheet_size_display = serializers.CharField()
    color_mode = serializers.CharField()
    color_mode_display = serializers.CharField()
    price_per_side = serializers.DecimalField(max_digits=10, decimal_places=2)
    price_double_sided = serializers.DecimalField(max_digits=10, decimal_places=2)


class SimpleRateCardPaperPriceSerializer(serializers.Serializer):
    """
    Simple paper price display for customers.
    Shows: "130gsm = KES 10, 150gsm = KES 15, 300gsm = KES 30"
    """
    
    gsm = serializers.IntegerField()
    paper_type = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, source="price_per_sheet")


class SimpleRateCardSerializer(serializers.Serializer):
    """
    Customer-friendly rate card showing simple pricing.
    
    Example output:
    {
        "print_prices": [
            {"sheet_size": "A3", "color_mode": "COLOR", "price_per_side": 15, "price_double_sided": 25}
        ],
        "paper_prices": {
            "A3": {
                "Gloss": [
                    {"gsm": 130, "price": 10},
                    {"gsm": 150, "price": 15},
                    {"gsm": 300, "price": 30}
                ]
            }
        },
        "how_to_calculate": "Total = (Print per side × number of sides) + Paper price"
    }
    """
    
    shop_name = serializers.CharField()
    print_prices = SimpleRateCardPrintPriceSerializer(many=True)
    paper_prices = serializers.DictField()
    how_to_calculate = serializers.CharField()
    examples = serializers.ListField(child=serializers.DictField())


class SimplePriceCalculatorInputSerializer(serializers.Serializer):
    """
    Input for simple price calculator.
    Customer provides: sheet_size, gsm, sides (1 or 2), quantity
    """
    
    sheet_size = serializers.ChoiceField(
        choices=PaperGSMPrice.SheetSize.choices,
        help_text="Paper size (e.g., A3, A4)"
    )
    gsm = serializers.IntegerField(
        min_value=60,
        max_value=500,
        help_text="Paper weight in GSM (e.g., 130, 150, 200, 300)"
    )
    paper_type = serializers.CharField(
        default="Gloss",
        help_text="Paper type (e.g., Gloss, Matte)"
    )
    sides = serializers.ChoiceField(
        choices=[(1, "Single-sided"), (2, "Double-sided")],
        help_text="Number of printed sides"
    )
    quantity = serializers.IntegerField(
        min_value=1,
        help_text="Number of sheets"
    )
    color_mode = serializers.ChoiceField(
        choices=DigitalPrintPrice.ColorMode.choices,
        default="COLOR",
        help_text="Color mode (COLOR or BW)"
    )


class SimplePriceCalculatorOutputSerializer(serializers.Serializer):
    """
    Output for simple price calculator.
    Shows clear breakdown that customer can understand.
    """
    
    # Input echo
    sheet_size = serializers.CharField()
    gsm = serializers.IntegerField()
    paper_type = serializers.CharField()
    sides = serializers.IntegerField()
    quantity = serializers.IntegerField()
    
    # Price breakdown
    print_price_per_side = serializers.DecimalField(max_digits=10, decimal_places=2)
    print_price_per_sheet = serializers.DecimalField(max_digits=10, decimal_places=2)
    paper_price_per_sheet = serializers.DecimalField(max_digits=10, decimal_places=2)
    price_per_sheet = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Totals
    total_print_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_paper_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # Human-readable breakdown
    breakdown_text = serializers.CharField()