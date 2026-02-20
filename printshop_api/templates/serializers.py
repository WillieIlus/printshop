# templates/serializers.py

from decimal import Decimal

from rest_framework import serializers

from .models import (
    TemplateCategory,
    PrintTemplate,
    TemplateFinishing,
    TemplateOption,
)


class TemplateCategorySerializer(serializers.ModelSerializer):
    """Serializer for template categories."""
    
    template_count = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon_svg_path",
            "display_order",
            "is_active",
            "template_count",
        ]

    def get_template_count(self, obj):
        return obj.print_templates.filter(is_active=True).count()


class TemplateFinishingSerializer(serializers.ModelSerializer):
    """Serializer for template finishing options."""

    class Meta:
        model = TemplateFinishing
        fields = [
            "id",
            "name",
            "description",
            "is_mandatory",
            "is_default",
            "price_adjustment",
            "display_order",
        ]


class TemplateOptionSerializer(serializers.ModelSerializer):
    """Serializer for template options."""
    
    option_type_display = serializers.CharField(
        source="get_option_type_display", 
        read_only=True
    )

    class Meta:
        model = TemplateOption
        fields = [
            "id",
            "option_type",
            "option_type_display",
            "label",
            "value",
            "price_modifier",
            "is_default",
            "display_order",
        ]


class PrintTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing templates in gallery."""
    
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    created_by_shop = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()
    starting_price = serializers.CharField(
        source="get_starting_price_display", 
        read_only=True
    )

    class Meta:
        model = PrintTemplate
        fields = [
            "id",
            "title",
            "slug",
            "category_name",
            "category_slug",
            "created_by_shop",
            "base_price",
            "starting_price",
            "preview_image",
            "dimensions_label",
            "weight_label",
            "badges",
            "min_quantity",
        ]

    def get_created_by_shop(self, obj):
        if obj.created_by_shop_id:
            return {
                "id": obj.created_by_shop.id,
                "name": obj.created_by_shop.name,
                "slug": obj.created_by_shop.slug,
            }
        return None

    def get_badges(self, obj):
        return obj.get_gallery_badges()


class PrintTemplateDetailSerializer(serializers.ModelSerializer):
    """Full serializer for template detail view."""
    
    category = TemplateCategorySerializer(read_only=True)
    finishing_options = TemplateFinishingSerializer(many=True, read_only=True)
    options = TemplateOptionSerializer(many=True, read_only=True)
    badges = serializers.SerializerMethodField()
    starting_price = serializers.CharField(
        source="get_starting_price_display", 
        read_only=True
    )
    print_sides_display = serializers.CharField(
        source="get_default_print_sides_display",
        read_only=True
    )
    
    # Grouped options for frontend
    grouped_options = serializers.SerializerMethodField()
    mandatory_finishing = serializers.SerializerMethodField()
    optional_finishing = serializers.SerializerMethodField()
    created_by_shop = serializers.SerializerMethodField()

    class Meta:
        model = PrintTemplate
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "category",
            "created_by_shop",
            "base_price",
            "starting_price",
            "min_quantity",
            "final_width",
            "final_height",
            "default_gsm",
            "min_gsm",
            "max_gsm",
            "allowed_gsm_values",
            "default_print_sides",
            "print_sides_display",
            "preview_image",
            "dimensions_label",
            "weight_label",
            "badges",
            "is_popular",
            "is_best_value",
            "is_new",
            "meta_description",
            "finishing_options",
            "options",
            "grouped_options",
            "mandatory_finishing",
            "optional_finishing",
            "created_at",
            "updated_at",
        ]

    def get_badges(self, obj):
        return obj.get_gallery_badges()

    def get_created_by_shop(self, obj):
        if obj.created_by_shop_id:
            return {
                "id": obj.created_by_shop.id,
                "name": obj.created_by_shop.name,
                "slug": obj.created_by_shop.slug,
            }
        return None

    def get_grouped_options(self, obj):
        """Group options by type for easier frontend rendering."""
        options = obj.options.all()
        grouped = {}
        for option in options:
            opt_type = option.get_option_type_display()
            if opt_type not in grouped:
                grouped[opt_type] = []
            grouped[opt_type].append(TemplateOptionSerializer(option).data)
        return grouped

    def get_mandatory_finishing(self, obj):
        """Return only mandatory finishing options."""
        return TemplateFinishingSerializer(
            obj.finishing_options.filter(is_mandatory=True),
            many=True
        ).data

    def get_optional_finishing(self, obj):
        """Return only optional finishing options."""
        return TemplateFinishingSerializer(
            obj.finishing_options.filter(is_mandatory=False),
            many=True
        ).data


class TemplateQuoteRequestSerializer(serializers.Serializer):
    """
    Serializer for converting a template into a quote request.
    Customer submits their selections and gets a quote.
    """
    
    template_id = serializers.IntegerField()
    shop_id = serializers.IntegerField(
        required=False,
        help_text="Optional shop ID. If not provided, best available shop is selected."
    )
    quantity = serializers.IntegerField(min_value=1)
    
    # Optional customizations
    gsm = serializers.IntegerField(required=False, allow_null=True)
    print_sides = serializers.ChoiceField(
        choices=[("SIMPLEX", "Single-sided"), ("DUPLEX", "Double-sided")],
        required=False
    )
    
    # Selected options (list of option IDs)
    selected_option_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )
    
    # Selected finishing (list of finishing IDs - mandatory ones are auto-included)
    selected_finishing_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )
    
    # Customer details
    customer_notes = serializers.CharField(
        required=False, 
        allow_blank=True,
        max_length=1000
    )


class TemplatePriceCalculationSerializer(serializers.Serializer):
    """
    Serializer for real-time price calculation when options change.
    Supports both digital (sheet-based) and large format (area-based) modes.

    Digital mode (default):
    - quantity (required)
    - sheet_size (optional; A5/A4/A3/SRA3)
    - print_sides (SIMPLEX/DUPLEX)
    - gsm (optional; default from template)
    - paper_type (optional; GLOSS/MATTE/BOND/ART)
    - machine_id (optional; not used in STRATEGY 1)
    - shop_slug or shop_id (optional; for shop-specific GSM capability enforcement)

    Large format mode (when unit=SQM or area/width/height/material_type provided):
    - unit = "SQM"
    - width_m, height_m (decimal) OR area_sqm (decimal)
    - quantity (required)
    - material_type (BANNER/VINYL/REFLECTIVE)
    """

    # Common
    quantity = serializers.IntegerField(min_value=1)

    # Shop for capability enforcement (optional; or use template.created_by_shop for gallery)
    shop_slug = serializers.SlugField(required=False, allow_null=True)
    shop_id = serializers.IntegerField(required=False, allow_null=True)

    # Digital mode
    sheet_size = serializers.ChoiceField(
        choices=[("A5", "A5"), ("A4", "A4"), ("A3", "A3"), ("SRA3", "SRA3")],
        required=False,
    )
    print_sides = serializers.ChoiceField(
        choices=[("SIMPLEX", "Single-sided"), ("DUPLEX", "Double-sided")],
        required=False,
    )
    gsm = serializers.IntegerField(required=False, allow_null=True, min_value=60, max_value=500)
    paper_type = serializers.ChoiceField(
        choices=[("GLOSS", "Gloss"), ("MATTE", "Matte"), ("BOND", "Bond"), ("ART", "Art Paper")],
        required=False,
    )
    machine_id = serializers.IntegerField(required=False, allow_null=True)

    # Large format mode
    unit = serializers.ChoiceField(
        choices=[("SHEET", "Sheet"), ("SQM", "Square meter")],
        required=False,
    )
    width_m = serializers.DecimalField(
        max_digits=10, decimal_places=4, required=False, allow_null=True, min_value=Decimal("0.01")
    )
    height_m = serializers.DecimalField(
        max_digits=10, decimal_places=4, required=False, allow_null=True, min_value=Decimal("0.01")
    )
    area_sqm = serializers.DecimalField(
        max_digits=10, decimal_places=4, required=False, allow_null=True, min_value=Decimal("0.01")
    )
    material_type = serializers.ChoiceField(
        choices=[("BANNER", "Banner"), ("VINYL", "Vinyl"), ("REFLECTIVE", "Reflective")],
        required=False,
    )

    # Options and finishing
    selected_option_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )
    selected_finishing_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        """Validate large format has required fields and GSM constraints for digital mode."""
        is_large = (
            attrs.get("unit") == "SQM"
            or attrs.get("area_sqm") is not None
            or (attrs.get("width_m") is not None and attrs.get("height_m") is not None)
            or attrs.get("material_type") is not None
        )
        if is_large:
            area = attrs.get("area_sqm")
            width = attrs.get("width_m")
            height = attrs.get("height_m")
            if area is None and (width is None or height is None):
                raise serializers.ValidationError(
                    "Large format requires area_sqm or both width_m and height_m"
                )
        else:
            # Digital mode: validate GSM against template and shop constraints
            template = self.context.get("template")
            if template:
                gsm = attrs.get("gsm") or template.default_gsm or 300
                sheet_size = attrs.get("sheet_size") or "A4"
                shop = None
                shop_slug = attrs.get("shop_slug")
                shop_id = attrs.get("shop_id")
                if shop_slug or shop_id:
                    from shops.models import Shop

                    if shop_slug:
                        shop = Shop.objects.filter(slug=shop_slug, is_active=True).first()
                        if not shop:
                            raise serializers.ValidationError(
                                {"shop_slug": "Shop not found or inactive"}
                            )
                    else:
                        shop = Shop.objects.filter(id=shop_id, is_active=True).first()
                        if not shop:
                            raise serializers.ValidationError(
                                {"shop_id": "Shop not found or inactive"}
                            )
                try:
                    from .services.gsm_validation import validate_gsm_for_calculation

                    validate_gsm_for_calculation(template, gsm, sheet_size, shop)
                except ValueError as e:
                    raise serializers.ValidationError({"gsm": str(e)})
        return attrs
