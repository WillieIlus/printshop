# templates/tests.py

from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from django.contrib.auth import get_user_model

from shops.models import Shop
from templates.models import (
    TemplateCategory,
    PrintTemplate,
    TemplateFinishing,
    TemplateOption,
)


User = get_user_model()


# =============================================================================
# Model Tests
# =============================================================================


class TemplateCategoryModelTests(TestCase):
    """Unit tests for TemplateCategory model."""
    
    def test_category_creation(self):
        """Test basic category creation."""
        category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards",
            description="Professional business cards"
        )
        self.assertEqual(str(category), "Business Cards")
        self.assertTrue(category.is_active)
    
    def test_slug_auto_generation(self):
        """Test that slug is auto-generated from name."""
        category = TemplateCategory.objects.create(
            name="Marketing Materials"
        )
        self.assertEqual(category.slug, "marketing-materials")
    
    def test_unique_slug_constraint(self):
        """Test unique slug constraint."""
        TemplateCategory.objects.create(
            name="Flyers",
            slug="flyers"
        )
        with self.assertRaises(IntegrityError):
            TemplateCategory.objects.create(
                name="Another Flyers",
                slug="flyers"  # Duplicate slug
            )
    
    def test_ordering_by_display_order(self):
        """Test categories are ordered by display_order then name."""
        cat3 = TemplateCategory.objects.create(
            name="Brochures",
            slug="brochures",
            display_order=3
        )
        cat1 = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards",
            display_order=1
        )
        cat2 = TemplateCategory.objects.create(
            name="Flyers",
            slug="flyers",
            display_order=2
        )
        
        categories = list(TemplateCategory.objects.all())
        self.assertEqual(categories[0], cat1)
        self.assertEqual(categories[1], cat2)
        self.assertEqual(categories[2], cat3)


class PrintTemplateModelTests(TestCase):
    """Unit tests for PrintTemplate model."""
    
    def setUp(self):
        """Set up test data."""
        self.category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards"
        )
    
    def test_template_creation(self):
        """Test basic template creation."""
        template = PrintTemplate.objects.create(
            title="Premium Business Cards",
            category=self.category,
            base_price=Decimal("1200.00"),
            min_quantity=100,
            dimensions_label="90 × 55 mm",
            weight_label="350gsm"
        )
        self.assertEqual(str(template), "Premium Business Cards")
        self.assertTrue(template.is_active)
    
    def test_slug_auto_generation(self):
        """Test that slug is auto-generated from title."""
        template = PrintTemplate.objects.create(
            title="Matte Finish Cards",
            category=self.category,
            base_price=Decimal("1000.00"),
            dimensions_label="85 × 55 mm",
            weight_label="300gsm"
        )
        self.assertEqual(template.slug, "matte-finish-cards")
    
    def test_get_starting_price_display(self):
        """Test formatted price display."""
        template = PrintTemplate.objects.create(
            title="Test Template",
            category=self.category,
            base_price=Decimal("1500.00"),
            dimensions_label="A5",
            weight_label="250gsm"
        )
        self.assertEqual(template.get_starting_price_display(), "KES 1,500")
    
    def test_get_gallery_badges_multiple(self):
        """Test gallery badges with multiple flags."""
        template = PrintTemplate.objects.create(
            title="Featured Cards",
            category=self.category,
            base_price=Decimal("1200.00"),
            is_popular=True,
            is_best_value=True,
            is_new=False,
            dimensions_label="90 × 55 mm",
            weight_label="350gsm"
        )
        badges = template.get_gallery_badges()
        self.assertEqual(badges, ["Popular", "Best Value"])
    
    def test_get_gallery_badges_empty(self):
        """Test gallery badges when no flags set."""
        template = PrintTemplate.objects.create(
            title="Standard Cards",
            category=self.category,
            base_price=Decimal("800.00"),
            is_popular=False,
            is_best_value=False,
            is_new=False,
            dimensions_label="85 × 55 mm",
            weight_label="300gsm"
        )
        badges = template.get_gallery_badges()
        self.assertEqual(badges, [])
    
    def test_product_specifications(self):
        """Test product specifications fields."""
        template = PrintTemplate.objects.create(
            title="Exact Size Cards",
            category=self.category,
            base_price=Decimal("1200.00"),
            final_width=Decimal("90.00"),
            final_height=Decimal("55.00"),
            default_gsm=350,
            default_print_sides="DUPLEX",
            dimensions_label="90 × 55 mm",
            weight_label="350gsm"
        )
        self.assertEqual(template.final_width, Decimal("90.00"))
        self.assertEqual(template.final_height, Decimal("55.00"))
        self.assertEqual(template.default_gsm, 350)
        self.assertEqual(template.default_print_sides, "DUPLEX")


class TemplateFinishingModelTests(TestCase):
    """Unit tests for TemplateFinishing model."""
    
    def setUp(self):
        """Set up test data."""
        self.category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards"
        )
        self.template = PrintTemplate.objects.create(
            title="Premium Cards",
            category=self.category,
            base_price=Decimal("1200.00"),
            dimensions_label="90 × 55 mm",
            weight_label="350gsm"
        )
    
    def test_finishing_creation(self):
        """Test basic finishing creation."""
        finishing = TemplateFinishing.objects.create(
            template=self.template,
            name="Matt Lamination",
            description="Smooth matte finish",
            is_mandatory=True,
            price_adjustment=Decimal("0.00")
        )
        self.assertTrue(finishing.is_mandatory)
        self.assertEqual(
            str(finishing),
            "Premium Cards - Matt Lamination (Mandatory)"
        )
    
    def test_optional_finishing(self):
        """Test optional finishing."""
        finishing = TemplateFinishing.objects.create(
            template=self.template,
            name="Spot UV",
            is_mandatory=False,
            is_default=True,
            price_adjustment=Decimal("200.00")
        )
        self.assertFalse(finishing.is_mandatory)
        self.assertTrue(finishing.is_default)
        self.assertEqual(finishing.price_adjustment, Decimal("200.00"))
        self.assertEqual(str(finishing), "Premium Cards - Spot UV")
    
    def test_ordering_by_display_order(self):
        """Test finishing options are ordered correctly."""
        f3 = TemplateFinishing.objects.create(
            template=self.template,
            name="Embossing",
            display_order=3
        )
        f1 = TemplateFinishing.objects.create(
            template=self.template,
            name="Lamination",
            display_order=1
        )
        f2 = TemplateFinishing.objects.create(
            template=self.template,
            name="Spot UV",
            display_order=2
        )
        
        finishings = list(self.template.finishing_options.all())
        self.assertEqual(finishings[0], f1)
        self.assertEqual(finishings[1], f2)
        self.assertEqual(finishings[2], f3)


class TemplateOptionModelTests(TestCase):
    """Unit tests for TemplateOption model."""
    
    def setUp(self):
        """Set up test data."""
        self.category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards"
        )
        self.template = PrintTemplate.objects.create(
            title="Customizable Cards",
            category=self.category,
            base_price=Decimal("1000.00"),
            dimensions_label="85 × 55 mm",
            weight_label="300gsm"
        )
    
    def test_option_creation(self):
        """Test basic option creation."""
        option = TemplateOption.objects.create(
            template=self.template,
            option_type="PAPER_GSM",
            label="350 GSM",
            value="350",
            price_modifier=Decimal("100.00"),
            is_default=True
        )
        self.assertEqual(
            str(option),
            "Customizable Cards - Paper Weight (GSM): 350 GSM"
        )
    
    def test_quantity_options(self):
        """Test quantity option type."""
        options_data = [
            ("100 pcs", "100", Decimal("0.00"), True),
            ("250 pcs", "250", Decimal("500.00"), False),
            ("500 pcs", "500", Decimal("800.00"), False),
        ]
        
        for label, value, modifier, is_default in options_data:
            TemplateOption.objects.create(
                template=self.template,
                option_type="QUANTITY",
                label=label,
                value=value,
                price_modifier=modifier,
                is_default=is_default
            )
        
        qty_options = self.template.options.filter(option_type="QUANTITY")
        self.assertEqual(qty_options.count(), 3)
        
        # Check default
        default = qty_options.get(is_default=True)
        self.assertEqual(default.label, "100 pcs")
    
    def test_multiple_option_types(self):
        """Test template with multiple option types."""
        # GSM options
        TemplateOption.objects.create(
            template=self.template,
            option_type="PAPER_GSM",
            label="300 GSM",
            value="300",
            is_default=True
        )
        TemplateOption.objects.create(
            template=self.template,
            option_type="PAPER_GSM",
            label="350 GSM",
            value="350",
            price_modifier=Decimal("50.00")
        )
        
        # Quantity options
        TemplateOption.objects.create(
            template=self.template,
            option_type="QUANTITY",
            label="100 pcs",
            value="100",
            is_default=True
        )
        
        self.assertEqual(
            self.template.options.filter(option_type="PAPER_GSM").count(),
            2
        )
        self.assertEqual(
            self.template.options.filter(option_type="QUANTITY").count(),
            1
        )


# =============================================================================
# API Tests
# =============================================================================


class TemplateCategoryAPITests(APITestCase):
    """API tests for template category endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards",
            is_active=True
        )
        self.inactive_category = TemplateCategory.objects.create(
            name="Archived",
            slug="archived",
            is_active=False
        )
        self.client = APIClient()
    
    def test_category_list_public_access(self):
        """Test category list is publicly accessible."""
        url = "/api/templates/categories/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_category_list_filters_inactive(self):
        """Test that inactive categories are filtered out."""
        url = "/api/templates/categories/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return active categories
        slugs = [c["slug"] for c in response.data]
        self.assertIn("business-cards", slugs)
        self.assertNotIn("archived", slugs)


class PrintTemplateAPITests(APITestCase):
    """API tests for print template endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards"
        )
        self.template = PrintTemplate.objects.create(
            title="Premium Business Cards",
            slug="premium-business-cards",
            category=self.category,
            base_price=Decimal("1200.00"),
            min_quantity=100,
            final_width=Decimal("90.00"),
            final_height=Decimal("55.00"),
            default_gsm=350,
            default_print_sides="DUPLEX",
            dimensions_label="90 × 55 mm",
            weight_label="350gsm",
            is_popular=True,
            is_active=True
        )
        self.inactive_template = PrintTemplate.objects.create(
            title="Archived Template",
            slug="archived-template",
            category=self.category,
            base_price=Decimal("500.00"),
            dimensions_label="N/A",
            weight_label="N/A",
            is_active=False
        )
        
        # Add finishing options
        TemplateFinishing.objects.create(
            template=self.template,
            name="Matt Lamination",
            is_mandatory=True,
            price_adjustment=Decimal("0.00")
        )
        TemplateFinishing.objects.create(
            template=self.template,
            name="Spot UV",
            is_mandatory=False,
            price_adjustment=Decimal("200.00")
        )
        
        # Add options
        TemplateOption.objects.create(
            template=self.template,
            option_type="QUANTITY",
            label="100 pcs",
            value="100",
            is_default=True
        )
        TemplateOption.objects.create(
            template=self.template,
            option_type="QUANTITY",
            label="250 pcs",
            value="250",
            price_modifier=Decimal("500.00")
        )
        
        self.client = APIClient()
    
    def test_template_list_public_access(self):
        """Test template list is publicly accessible."""
        url = "/api/templates/templates/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_template_list_filters_inactive(self):
        """Test that inactive templates are filtered out."""
        url = "/api/templates/templates/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [t["slug"] for t in response.data]
        self.assertIn("premium-business-cards", slugs)
        self.assertNotIn("archived-template", slugs)
    
    def test_template_detail(self):
        """Test template detail endpoint."""
        url = f"/api/templates/templates/{self.template.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Premium Business Cards")
        self.assertIn("finishing_options", response.data)
        self.assertIn("options", response.data)
    
    def test_template_filter_by_category(self):
        """Test filtering templates by category."""
        url = f"/api/templates/templates/?category={self.category.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only active templates in this category
        self.assertEqual(len(response.data), 1)
    
    def test_template_search(self):
        """Test searching templates."""
        url = "/api/templates/templates/?search=premium"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Premium Business Cards")


class TemplateGalleryAPITests(APITestCase):
    """API tests for template gallery endpoint."""
    
    def setUp(self):
        """Set up test data."""
        # Create multiple categories
        self.cat_cards = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards",
            display_order=1
        )
        self.cat_flyers = TemplateCategory.objects.create(
            name="Flyers",
            slug="flyers",
            display_order=2
        )
        
        # Create templates for each category
        PrintTemplate.objects.create(
            title="Standard Cards",
            slug="standard-cards",
            category=self.cat_cards,
            base_price=Decimal("800.00"),
            dimensions_label="85 × 55 mm",
            weight_label="300gsm"
        )
        PrintTemplate.objects.create(
            title="Premium Cards",
            slug="premium-cards",
            category=self.cat_cards,
            base_price=Decimal("1200.00"),
            is_popular=True,
            dimensions_label="90 × 55 mm",
            weight_label="350gsm"
        )
        PrintTemplate.objects.create(
            title="A5 Flyers",
            slug="a5-flyers",
            category=self.cat_flyers,
            base_price=Decimal("500.00"),
            dimensions_label="148 × 210 mm",
            weight_label="170gsm"
        )
        
        self.client = APIClient()
    
    def test_gallery_public_access(self):
        """Test gallery endpoint is publicly accessible."""
        url = "/api/templates/gallery/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_gallery_structure(self):
        """Test gallery returns categories with templates."""
        url = "/api/templates/gallery/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have categories with templates nested
        self.assertIn("categories", response.data)
        categories = response.data["categories"]
        
        # Find business cards category
        cards_cat = next(
            (c for c in categories if c["slug"] == "business-cards"),
            None
        )
        self.assertIsNotNone(cards_cat)
        self.assertEqual(len(cards_cat["templates"]), 2)


class TemplateQuoteRequestAPITests(APITestCase):
    """API tests for template-to-quote conversion."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.user,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            is_active=True,
            is_verified=True
        )
        self.category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards"
        )
        self.template = PrintTemplate.objects.create(
            title="Premium Business Cards",
            slug="premium-business-cards",
            category=self.category,
            base_price=Decimal("1200.00"),
            min_quantity=100,
            final_width=Decimal("90.00"),
            final_height=Decimal("55.00"),
            default_gsm=350,
            default_print_sides="DUPLEX",
            dimensions_label="90 × 55 mm",
            weight_label="350gsm"
        )
        
        # Add quantity options
        self.qty_100 = TemplateOption.objects.create(
            template=self.template,
            option_type="QUANTITY",
            label="100 pcs",
            value="100",
            price_modifier=Decimal("0.00"),
            is_default=True
        )
        self.qty_250 = TemplateOption.objects.create(
            template=self.template,
            option_type="QUANTITY",
            label="250 pcs",
            value="250",
            price_modifier=Decimal("500.00")
        )
        
        self.client = APIClient()
    
    def test_calculate_price_endpoint(self):
        """Test price calculation endpoint returns stable schema."""
        url = f"/api/templates/{self.template.slug}/calculate-price/"
        data = {
            "quantity": 250,
            "selected_option_ids": [self.qty_250.id],
            "selected_finishing_ids": [],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("printing", response.data)
        self.assertIn("material", response.data)
        self.assertIn("finishing", response.data)
        self.assertIn("subtotal", response.data)
        self.assertIn("total", response.data)
        self.assertIn("notes", response.data)
    
    def test_create_quote_requires_auth(self):
        """Test that quote creation requires authentication."""
        url = f"/api/templates/templates/{self.template.id}/create_quote/"
        data = {
            "shop_slug": self.shop.slug,
            "quantity": 100,
            "notes": "Please deliver by Friday"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_quote_authenticated(self):
        """Test authenticated user can create quote from template."""
        self.client.force_authenticate(user=self.user)
        url = f"/api/templates/templates/{self.template.id}/create_quote/"
        data = {
            "shop_slug": self.shop.slug,
            "quantity": 100,
            "notes": "Please deliver by Friday"
        }
        response = self.client.post(url, data, format="json")
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])


class TemplatePriceCalculationTests(TestCase):
    """Integration tests for template price calculations."""

    def setUp(self):
        """Set up test data."""
        self.category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards"
        )
        self.template = PrintTemplate.objects.create(
            title="Configurable Cards",
            slug="configurable-cards",
            category=self.category,
            base_price=Decimal("1000.00"),
            min_quantity=100,
            default_gsm=300,
            default_print_sides="DUPLEX",
            dimensions_label="85 × 55 mm",
            weight_label="300gsm"
        )

        # GSM options
        self.gsm_300 = TemplateOption.objects.create(
            template=self.template,
            option_type="PAPER_GSM",
            label="300 GSM",
            value="300",
            price_modifier=Decimal("0.00"),
            is_default=True
        )
        self.gsm_350 = TemplateOption.objects.create(
            template=self.template,
            option_type="PAPER_GSM",
            label="350 GSM",
            value="350",
            price_modifier=Decimal("100.00")
        )

        # Quantity options
        self.qty_100 = TemplateOption.objects.create(
            template=self.template,
            option_type="QUANTITY",
            label="100 pcs",
            value="100",
            price_modifier=Decimal("0.00"),
            is_default=True
        )
        self.qty_250 = TemplateOption.objects.create(
            template=self.template,
            option_type="QUANTITY",
            label="250 pcs",
            value="250",
            price_modifier=Decimal("600.00")
        )

        # Finishing options
        self.lam = TemplateFinishing.objects.create(
            template=self.template,
            name="Matt Lamination",
            is_mandatory=True,
            price_adjustment=Decimal("0.00")  # Included in base
        )
        self.spot_uv = TemplateFinishing.objects.create(
            template=self.template,
            name="Spot UV",
            is_mandatory=False,
            price_adjustment=Decimal("200.00")
        )

    def test_base_price_calculation(self):
        """Test base price with defaults."""
        total_modifiers = sum(
            opt.price_modifier
            for opt in self.template.options.filter(is_default=True)
        )
        total_modifiers += sum(
            fin.price_adjustment
            for fin in self.template.finishing_options.filter(is_mandatory=True)
        )
        expected_price = self.template.base_price + total_modifiers
        self.assertEqual(expected_price, Decimal("1000.00"))

    def test_upgraded_options_calculation(self):
        """Test price with upgraded options."""
        selected_options = [self.gsm_350, self.qty_250]
        selected_finishing = [self.spot_uv]
        total = self.template.base_price
        total += sum(opt.price_modifier for opt in selected_options)
        total += sum(fin.price_adjustment for fin in selected_finishing)
        self.assertEqual(total, Decimal("1900.00"))

    def test_mandatory_finishing_always_included(self):
        """Test that mandatory finishing is always part of total."""
        mandatory_finishings = self.template.finishing_options.filter(is_mandatory=True)
        self.assertEqual(mandatory_finishings.count(), 1)
        self.assertEqual(mandatory_finishings.first().name, "Matt Lamination")

    def test_optional_finishing_can_be_selected(self):
        """Test that optional finishing can be added."""
        optional_finishings = self.template.finishing_options.filter(is_mandatory=False)
        self.assertEqual(optional_finishings.count(), 1)
        spot_uv = optional_finishings.first()
        self.assertEqual(spot_uv.name, "Spot UV")
        self.assertEqual(spot_uv.price_adjustment, Decimal("200.00"))


class TemplateCalculatePriceAPITests(APITestCase):
    """API tests for POST /api/templates/{slug}/calculate-price/ endpoint."""

    def setUp(self):
        """Set up test data."""
        self.category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards",
        )
        self.template = PrintTemplate.objects.create(
            title="Premium Cards",
            slug="premium-cards",
            category=self.category,
            base_price=Decimal("1200.00"),
            min_quantity=100,
            default_gsm=300,
            default_print_sides="DUPLEX",
            dimensions_label="90 × 55 mm",
            weight_label="300gsm",
            is_active=True,
        )
        TemplateFinishing.objects.create(
            template=self.template,
            name="Matt Lamination",
            is_mandatory=True,
            price_adjustment=Decimal("0.00"),
        )
        TemplateFinishing.objects.create(
            template=self.template,
            name="Spot UV",
            is_mandatory=False,
            price_adjustment=Decimal("150.00"),
        )
        self.client = APIClient()

    def test_response_schema_stable(self):
        """Test response has stable schema: printing, material, finishing, subtotal, total, notes."""
        url = f"/api/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(url, {"quantity": 100}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ("printing", "material", "finishing", "subtotal", "total", "notes"):
            self.assertIn(key, response.data, f"Missing key: {key}")
        self.assertIn("amount", response.data["printing"])
        self.assertIn("details", response.data["printing"])
        self.assertIn("items", response.data["finishing"])
        self.assertIn("Demo estimate only", response.data["notes"][0])

    def test_simplex_vs_duplex_not_double(self):
        """Test duplex is not 2x simplex (uses ~1.4x multiplier)."""
        url = f"/api/templates/{self.template.slug}/calculate-price/"
        simplex = self.client.post(
            url, {"quantity": 100, "print_sides": "SIMPLEX"}, format="json"
        )
        duplex = self.client.post(
            url, {"quantity": 100, "print_sides": "DUPLEX"}, format="json"
        )
        self.assertEqual(simplex.status_code, status.HTTP_200_OK)
        self.assertEqual(duplex.status_code, status.HTTP_200_OK)
        # Parse amounts (e.g. "KES 1,200.00")
        def parse_kes(s):
            return Decimal(s.replace("KES ", "").replace(",", ""))
        total_simplex = parse_kes(simplex.data["total"])
        total_duplex = parse_kes(duplex.data["total"])
        # Duplex should be more than simplex but less than 2x
        self.assertGreater(total_duplex, total_simplex)
        self.assertLess(total_duplex, total_simplex * 2)

    def test_gsm_change_affects_total(self):
        """Test higher GSM increases total."""
        url = f"/api/templates/{self.template.slug}/calculate-price/"
        low_gsm = self.client.post(
            url, {"quantity": 100, "gsm": 200}, format="json"
        )
        high_gsm = self.client.post(
            url, {"quantity": 100, "gsm": 400}, format="json"
        )
        self.assertEqual(low_gsm.status_code, status.HTTP_200_OK)
        self.assertEqual(high_gsm.status_code, status.HTTP_200_OK)

        def parse_kes(s):
            return Decimal(s.replace("KES ", "").replace(",", ""))

        self.assertGreater(
            parse_kes(high_gsm.data["total"]),
            parse_kes(low_gsm.data["total"]),
        )

    def test_mandatory_finishing_always_included(self):
        """Test mandatory finishing appears in finishing items."""
        url = f"/api/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(url, {"quantity": 100}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data["finishing"]["items"]
        mandatory_names = [i["name"] for i in items if i["is_mandatory"]]
        self.assertIn("Matt Lamination", mandatory_names)

    def test_large_format_uses_area_sqm(self):
        """Test large format mode uses area-based pricing."""
        # Create a large-format style template
        lf_template = PrintTemplate.objects.create(
            title="Banner",
            slug="banner",
            category=self.category,
            base_price=Decimal("500.00"),  # per sqm
            min_quantity=1,
            dimensions_label="Custom",
            weight_label="N/A",
            is_active=True,
        )
        url = f"/api/templates/{lf_template.slug}/calculate-price/"
        # 2m x 1m = 2 sqm, qty 5
        response = self.client.post(
            url,
            {
                "quantity": 5,
                "width_m": 2,
                "height_m": 1,
                "material_type": "BANNER",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 500 * 2 * 5 = 5000
        self.assertIn("material", response.data)
        self.assertIn("area_sqm", str(response.data["material"]["details"]))
        total = Decimal(
            response.data["total"].replace("KES ", "").replace(",", "")
        )
        self.assertEqual(total, Decimal("5000.00"))

    def test_min_quantity_validation(self):
        """Test quantity below min_quantity returns 400."""
        url = f"/api/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(url, {"quantity": 50}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Minimum quantity", response.data["error"])
