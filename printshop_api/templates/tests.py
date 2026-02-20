# templates/tests.py

from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from django.contrib.auth import get_user_model

from shops.models import Shop, ShopPaperCapability
from templates.models import (
    TemplateCategory,
    PrintTemplate,
    TemplateFinishing,
    TemplateOption,
)


User = get_user_model()


def _create_shop(user=None):
    if user is None:
        user = User.objects.create_user(email="shop@test.com", password="test123")
    return Shop.objects.create(
        owner=user,
        name="Test Shop",
        slug="test-shop",
        business_email="shop@test.com",
        address_line="123 St",
        city="City",
        zip_code="00000",
        country="Country",
        is_active=True,
    )


# =============================================================================
# Model Tests
# =============================================================================


class TemplateCategoryModelTests(TestCase):
    """Unit tests for TemplateCategory model."""

    def test_category_creation(self):
        category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards",
            description="Professional business cards"
        )
        self.assertEqual(str(category), "Business Cards")
        self.assertTrue(category.is_active)

    def test_slug_auto_generation(self):
        category = TemplateCategory.objects.create(name="Marketing Materials")
        self.assertEqual(category.slug, "marketing-materials")

    def test_unique_slug_constraint(self):
        TemplateCategory.objects.create(name="Flyers", slug="flyers")
        with self.assertRaises(IntegrityError):
            TemplateCategory.objects.create(name="Another Flyers", slug="flyers")

    def test_ordering_by_display_order(self):
        cat3 = TemplateCategory.objects.create(name="Brochures", slug="brochures", display_order=3)
        cat1 = TemplateCategory.objects.create(name="Business Cards", slug="business-cards", display_order=1)
        cat2 = TemplateCategory.objects.create(name="Flyers", slug="flyers", display_order=2)
        categories = list(TemplateCategory.objects.all())
        self.assertEqual(categories[0], cat1)
        self.assertEqual(categories[1], cat2)
        self.assertEqual(categories[2], cat3)


class PrintTemplateModelTests(TestCase):
    """Unit tests for PrintTemplate model."""

    def setUp(self):
        self.shop = _create_shop()
        self.category = TemplateCategory.objects.create(name="Business Cards", slug="business-cards")

    def test_template_creation(self):
        template = PrintTemplate.objects.create(
            shop=self.shop,
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
        template = PrintTemplate.objects.create(
            shop=self.shop,
            title="Matte Finish Cards",
            category=self.category,
            base_price=Decimal("1000.00"),
            dimensions_label="85 × 55 mm",
            weight_label="300gsm"
        )
        self.assertEqual(template.slug, "matte-finish-cards")

    def test_get_starting_price_display(self):
        template = PrintTemplate.objects.create(
            shop=self.shop,
            title="Test Template",
            category=self.category,
            base_price=Decimal("1500.00"),
            dimensions_label="A5",
            weight_label="250gsm"
        )
        self.assertEqual(template.get_starting_price_display(), "KES 1,500")

    def test_get_gallery_badges_multiple(self):
        template = PrintTemplate.objects.create(
            shop=self.shop,
            title="Featured Cards",
            category=self.category,
            base_price=Decimal("1200.00"),
            is_popular=True,
            is_best_value=True,
            is_new=False,
            dimensions_label="90 × 55 mm",
            weight_label="350gsm"
        )
        self.assertEqual(template.get_gallery_badges(), ["Popular", "Best Value"])

    def test_get_gallery_badges_empty(self):
        template = PrintTemplate.objects.create(
            shop=self.shop,
            title="Standard Cards",
            category=self.category,
            base_price=Decimal("800.00"),
            is_popular=False,
            is_best_value=False,
            is_new=False,
            dimensions_label="85 × 55 mm",
            weight_label="300gsm"
        )
        self.assertEqual(template.get_gallery_badges(), [])

    def test_product_specifications(self):
        template = PrintTemplate.objects.create(
            shop=self.shop,
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

    def test_gsm_constraints_min_max_validation(self):
        """Test min_gsm <= max_gsm validation."""
        from django.core.exceptions import ValidationError
        template = PrintTemplate(
            shop=self.shop,
            title="Bad",
            category=self.category,
            base_price=Decimal("100"),
            min_gsm=400,
            max_gsm=200,
            dimensions_label="A5",
            weight_label="N/A",
        )
        with self.assertRaises(ValidationError):
            template.full_clean()


class TemplateFinishingModelTests(TestCase):
    """Unit tests for TemplateFinishing model."""

    def setUp(self):
        self.shop = _create_shop()
        self.category = TemplateCategory.objects.create(name="Business Cards", slug="business-cards")
        self.template = PrintTemplate.objects.create(
            shop=self.shop,
            title="Premium Cards",
            category=self.category,
            base_price=Decimal("1200.00"),
            dimensions_label="90 × 55 mm",
            weight_label="350gsm"
        )

    def test_finishing_creation(self):
        finishing = TemplateFinishing.objects.create(
            template=self.template,
            name="Matt Lamination",
            description="Smooth matte finish",
            is_mandatory=True,
            price_adjustment=Decimal("0.00")
        )
        self.assertTrue(finishing.is_mandatory)
        self.assertIn("Mandatory", str(finishing))

    def test_optional_finishing(self):
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


class TemplateOptionModelTests(TestCase):
    """Unit tests for TemplateOption model."""

    def setUp(self):
        self.shop = _create_shop()
        self.category = TemplateCategory.objects.create(name="Business Cards", slug="business-cards")
        self.template = PrintTemplate.objects.create(
            shop=self.shop,
            title="Customizable Cards",
            category=self.category,
            base_price=Decimal("1000.00"),
            dimensions_label="85 × 55 mm",
            weight_label="300gsm"
        )

    def test_option_creation(self):
        option = TemplateOption.objects.create(
            template=self.template,
            option_type="PAPER_GSM",
            label="350 GSM",
            value="350",
            price_modifier=Decimal("100.00"),
            is_default=True
        )
        self.assertIn("350 GSM", str(option))


# =============================================================================
# API Tests - Shop-scoped endpoints
# =============================================================================


class ShopTemplateCategoryAPITests(APITestCase):
    """API tests for shop-scoped template categories."""

    def setUp(self):
        self.shop = _create_shop()
        self.category = TemplateCategory.objects.create(
            name="Business Cards",
            slug="business-cards",
            is_active=True
        )
        PrintTemplate.objects.create(
            shop=self.shop,
            title="Premium Cards",
            slug="premium-cards",
            category=self.category,
            base_price=Decimal("1200"),
            dimensions_label="90×55",
            weight_label="350gsm",
            is_active=True,
        )
        self.client = APIClient()

    def test_category_list_shop_scoped(self):
        url = f"/api/shops/{self.shop.slug}/template-categories/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        slugs = [c["slug"] for c in data]
        self.assertIn("business-cards", slugs)


class ShopPrintTemplateAPITests(APITestCase):
    """API tests for shop-scoped print template endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")
        self.shop = _create_shop(self.user)
        self.other_shop = Shop.objects.create(
            owner=self.user,
            name="Other Shop",
            slug="other-shop",
            business_email="other@test.com",
            address_line="456 St",
            city="City",
            zip_code="00000",
            country="Country",
            is_active=True,
        )
        self.category = TemplateCategory.objects.create(name="Business Cards", slug="business-cards")
        self.template = PrintTemplate.objects.create(
            shop=self.shop,
            title="Premium Business Cards",
            slug="premium-business-cards",
            category=self.category,
            base_price=Decimal("1200.00"),
            min_quantity=100,
            dimensions_label="90 × 55 mm",
            weight_label="350gsm",
            is_popular=True,
            is_active=True
        )
        self.template_other_shop = PrintTemplate.objects.create(
            shop=self.other_shop,
            title="Other Shop Cards",
            slug="other-shop-cards",
            category=self.category,
            base_price=Decimal("800.00"),
            dimensions_label="85 × 55 mm",
            weight_label="300gsm",
            is_active=True
        )
        TemplateFinishing.objects.create(
            template=self.template,
            name="Matt Lamination",
            is_mandatory=True,
            price_adjustment=Decimal("0.00")
        )
        self.client = APIClient()

    def test_template_list_shop_scoped(self):
        """Templates list returns only templates for the shop."""
        url = f"/api/shops/{self.shop.slug}/templates/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        slugs = [t["template_slug"] for t in data]
        self.assertIn("premium-business-cards", slugs)
        self.assertNotIn("other-shop-cards", slugs)

    def test_template_detail_shop_scoped(self):
        url = f"/api/shops/{self.shop.slug}/templates/{self.template.slug}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Premium Business Cards")
        self.assertIn("template_slug", response.data)
        self.assertIn("constraints", response.data)
        self.assertIn("grouped_options", response.data)
        self.assertIn("finishing_options", response.data)

    def test_wrong_shop_slug_returns_404(self):
        """Cannot fetch a template using wrong shop slug."""
        url = f"/api/shops/{self.other_shop.slug}/templates/{self.template.slug}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_calculate_price_wrong_shop_404(self):
        """Calculate price with wrong shop slug returns 404."""
        url = f"/api/shops/{self.other_shop.slug}/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(url, {"quantity": 100}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ShopTemplateGSMConstraintTests(APITestCase):
    """Tests for GSM constraint enforcement in calculate-price."""

    def setUp(self):
        self.shop = _create_shop()
        self.category = TemplateCategory.objects.create(name="Business Cards", slug="business-cards")
        self.template = PrintTemplate.objects.create(
            shop=self.shop,
            title="GSM Constrained",
            slug="gsm-constrained",
            category=self.category,
            base_price=Decimal("1200"),
            min_quantity=100,
            min_gsm=200,
            max_gsm=350,
            dimensions_label="90×55",
            weight_label="300gsm",
            is_active=True,
        )
        self.client = APIClient()

    def test_gsm_below_min_returns_400(self):
        url = f"/api/shops/{self.shop.slug}/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(url, {"quantity": 100, "gsm": 150}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("below", response.data["error"].lower())

    def test_gsm_above_max_returns_400(self):
        url = f"/api/shops/{self.shop.slug}/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(url, {"quantity": 100, "gsm": 400}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("exceed", response.data["error"].lower())

    def test_gsm_in_range_succeeds(self):
        url = f"/api/shops/{self.shop.slug}/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(url, {"quantity": 100, "gsm": 300}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_allowed_gsm_values_enforcement(self):
        """When allowed_gsm_values is set, gsm must be in list."""
        self.template.allowed_gsm_values = [250, 300, 350]
        self.template.min_gsm = None
        self.template.max_gsm = None
        self.template.save()

        url = f"/api/shops/{self.shop.slug}/templates/{self.template.slug}/calculate-price/"
        # 300 is allowed
        r1 = self.client.post(url, {"quantity": 100, "gsm": 300}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        # 200 is not in list
        r2 = self.client.post(url, {"quantity": 100, "gsm": 200}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not allowed", r2.data["error"])


class ShopCapabilityEnforcementTests(APITestCase):
    """Tests for shop paper capability enforcement."""

    def setUp(self):
        self.shop = _create_shop()
        self.category = TemplateCategory.objects.create(name="Business Cards", slug="business-cards")
        self.template = PrintTemplate.objects.create(
            shop=self.shop,
            title="Cards",
            slug="cards",
            category=self.category,
            base_price=Decimal("1200"),
            min_quantity=100,
            dimensions_label="90×55",
            weight_label="300gsm",
            is_active=True,
        )
        # Shop can only do 150-350 GSM for A4
        ShopPaperCapability.objects.create(
            shop=self.shop,
            sheet_size="A4",
            min_gsm=150,
            max_gsm=350,
        )
        self.client = APIClient()

    def test_gsm_below_shop_min_returns_400(self):
        url = f"/api/shops/{self.shop.slug}/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(
            url,
            {"quantity": 100, "gsm": 100, "sheet_size": "A4"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("shop minimum", response.data["error"].lower())

    def test_gsm_above_shop_max_returns_400(self):
        url = f"/api/shops/{self.shop.slug}/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(
            url,
            {"quantity": 100, "gsm": 400, "sheet_size": "A4"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("shop maximum", response.data["error"].lower())

    def test_gsm_within_shop_capability_succeeds(self):
        url = f"/api/shops/{self.shop.slug}/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(
            url,
            {"quantity": 100, "gsm": 250, "sheet_size": "A4"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ShopTemplateCalculatePriceAPITests(APITestCase):
    """API tests for shop-scoped calculate-price endpoint."""

    def setUp(self):
        self.shop = _create_shop()
        self.category = TemplateCategory.objects.create(name="Business Cards", slug="business-cards")
        self.template = PrintTemplate.objects.create(
            shop=self.shop,
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
        url = f"/api/shops/{self.shop.slug}/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(url, {"quantity": 100}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ("printing", "material", "finishing", "subtotal", "total", "notes"):
            self.assertIn(key, response.data, f"Missing key: {key}")
        self.assertIn("amount", response.data["printing"])
        self.assertIn("items", response.data["finishing"])

    def test_min_quantity_validation(self):
        url = f"/api/shops/{self.shop.slug}/templates/{self.template.slug}/calculate-price/"
        response = self.client.post(url, {"quantity": 50}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Minimum quantity", response.data["error"])

    def test_large_format_uses_area_sqm(self):
        lf_template = PrintTemplate.objects.create(
            shop=self.shop,
            title="Banner",
            slug="banner",
            category=self.category,
            base_price=Decimal("500.00"),
            min_quantity=1,
            dimensions_label="Custom",
            weight_label="N/A",
            is_active=True,
        )
        url = f"/api/shops/{self.shop.slug}/templates/{lf_template.slug}/calculate-price/"
        response = self.client.post(
            url,
            {"quantity": 5, "width_m": 2, "height_m": 1, "material_type": "BANNER"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("material", response.data)
        total = Decimal(response.data["total"].replace("KES ", "").replace(",", ""))
        self.assertEqual(total, Decimal("5000.00"))
