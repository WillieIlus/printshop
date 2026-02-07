# quotes/tests.py

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from django.contrib.auth import get_user_model

from shops.models import Shop
from inventory.models import Machine, Material, MaterialStock
from pricing.models import DigitalPrintPrice, MaterialPrice, FinishingPrice, PricingTier
from quotes.models import Quote, QuoteItem, QuoteItemPart, QuoteItemFinishing, ProductTemplate
from quotes.services import QuoteCalculator


User = get_user_model()


# =============================================================================
# Model Tests
# =============================================================================


class QuoteModelTests(TestCase):
    """Unit tests for Quote model."""
    
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
            business_email="shop@example.com"
        )
    
    def test_quote_creation(self):
        """Test basic quote creation."""
        quote = Quote.objects.create(
            shop=self.shop,
            user=self.user,
            title="Test Quote"
        )
        self.assertEqual(quote.status, Quote.Status.DRAFT)
        self.assertEqual(quote.net_total, Decimal("0.00"))
        self.assertEqual(quote.tax_rate, Decimal("16.00"))
    
    def test_reference_auto_generation(self):
        """Test that reference is auto-generated on save."""
        quote = Quote.objects.create(
            shop=self.shop,
            user=self.user,
            title="Test Quote"
        )
        self.assertIsNotNone(quote.reference)
        self.assertTrue(quote.reference.startswith("Q-"))
    
    def test_reference_uniqueness_per_month(self):
        """Test references are unique within a month."""
        quote1 = Quote.objects.create(
            shop=self.shop,
            user=self.user,
            title="Quote 1"
        )
        quote2 = Quote.objects.create(
            shop=self.shop,
            user=self.user,
            title="Quote 2"
        )
        self.assertNotEqual(quote1.reference, quote2.reference)
        
        # References should have sequential numbers
        ref1_num = int(quote1.reference.split("-")[-1])
        ref2_num = int(quote2.reference.split("-")[-1])
        self.assertEqual(ref2_num, ref1_num + 1)
    
    def test_is_expired_property(self):
        """Test is_expired property."""
        # Not expired
        quote = Quote.objects.create(
            shop=self.shop,
            user=self.user,
            valid_until=timezone.now().date() + timedelta(days=7)
        )
        self.assertFalse(quote.is_expired)
        
        # Expired
        quote.valid_until = timezone.now().date() - timedelta(days=1)
        quote.save()
        self.assertTrue(quote.is_expired)
        
        # No expiry date
        quote.valid_until = None
        quote.save()
        self.assertFalse(quote.is_expired)
    
    def test_str_representation(self):
        """Test string representation."""
        quote = Quote.objects.create(
            shop=self.shop,
            user=self.user,
            title="Business Cards Order"
        )
        expected = f"Quote #{quote.id} - {quote.reference}"
        self.assertEqual(str(quote), expected)


class QuoteItemModelTests(TestCase):
    """Unit tests for QuoteItem model."""
    
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
            business_email="shop@example.com"
        )
        self.quote = Quote.objects.create(
            shop=self.shop,
            user=self.user,
            title="Test Quote"
        )
    
    def test_quote_item_creation(self):
        """Test basic quote item creation."""
        item = QuoteItem.objects.create(
            quote=self.quote,
            name="Business Cards",
            quantity=500
        )
        self.assertEqual(item.calculated_price, Decimal("0.00"))
    
    def test_str_representation(self):
        """Test string representation."""
        item = QuoteItem.objects.create(
            quote=self.quote,
            name="Annual Reports",
            quantity=200
        )
        self.assertEqual(str(item), "200 x Annual Reports")


class ProductTemplateModelTests(TestCase):
    """Unit tests for ProductTemplate model."""
    
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
            business_email="shop@example.com"
        )
    
    def test_product_template_creation(self):
        """Test product template creation."""
        template = ProductTemplate.objects.create(
            shop=self.shop,
            name="Standard Business Card",
            description="85x55mm double-sided cards",
            defaults={
                "final_width": 85,
                "final_height": 55,
                "print_sides": "DUPLEX"
            }
        )
        self.assertTrue(template.is_active)
        self.assertEqual(template.defaults["final_width"], 85)
    
    def test_str_representation(self):
        """Test string representation."""
        template = ProductTemplate.objects.create(
            shop=self.shop,
            name="A5 Flyer Template"
        )
        self.assertEqual(str(template), "A5 Flyer Template")


# =============================================================================
# QuoteCalculator Service Tests
# =============================================================================


class QuoteCalculatorImpositionTests(TestCase):
    """Unit tests for QuoteCalculator.calculate_imposition."""
    
    def test_business_cards_on_sra3(self):
        """Test business card imposition on SRA3."""
        # SRA3 = 320x450mm, Business card = 85x55mm
        items_per_sheet = QuoteCalculator.calculate_imposition(
            part_width=Decimal("85"),
            part_height=Decimal("55"),
            stock_width=Decimal("320"),
            stock_height=Decimal("450")
        )
        # Standard orientation: 320/85=3, 450/55=8 = 24
        # Rotated: 320/55=5, 450/85=5 = 25
        self.assertEqual(items_per_sheet, 25)
    
    def test_a5_flyer_on_a3(self):
        """Test A5 flyer imposition on A3."""
        # A3 = 297x420mm, A5 = 148x210mm
        items_per_sheet = QuoteCalculator.calculate_imposition(
            part_width=Decimal("148"),
            part_height=Decimal("210"),
            stock_width=Decimal("297"),
            stock_height=Decimal("420")
        )
        # Standard: 297/148=2, 420/210=2 = 4
        self.assertEqual(items_per_sheet, 4)
    
    def test_a4_on_a3(self):
        """Test A4 imposition on A3."""
        # A3 = 297x420mm, A4 = 210x297mm
        items_per_sheet = QuoteCalculator.calculate_imposition(
            part_width=Decimal("210"),
            part_height=Decimal("297"),
            stock_width=Decimal("297"),
            stock_height=Decimal("420")
        )
        # Standard: 297/210=1, 420/297=1 = 1
        # Rotated: 297/297=1, 420/210=2 = 2
        self.assertEqual(items_per_sheet, 2)
    
    def test_part_too_large_for_stock(self):
        """Test that parts larger than stock return 0."""
        items_per_sheet = QuoteCalculator.calculate_imposition(
            part_width=Decimal("500"),
            part_height=Decimal("500"),
            stock_width=Decimal("320"),
            stock_height=Decimal("450")
        )
        self.assertEqual(items_per_sheet, 0)
    
    def test_part_exactly_fits_stock(self):
        """Test part that exactly fits stock."""
        items_per_sheet = QuoteCalculator.calculate_imposition(
            part_width=Decimal("320"),
            part_height=Decimal("450"),
            stock_width=Decimal("320"),
            stock_height=Decimal("450")
        )
        self.assertEqual(items_per_sheet, 1)


class QuoteCalculatorPartCostTests(TestCase):
    """Unit tests for QuoteCalculator.calculate_part_cost."""
    
    def setUp(self):
        """Set up test data for part cost calculations."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.user,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com"
        )
        self.machine = Machine.objects.create(
            shop=self.shop,
            name="Xerox V80",
            type="DIGITAL",
            is_active=True
        )
        self.material = Material.objects.create(
            shop=self.shop,
            name="300gsm Art Card",
            type="SHEET",
            cost_per_unit=Decimal("8.00"),
            unit_type="PER_SHEET",
            is_active=True
        )
        self.stock = MaterialStock.objects.create(
            material=self.material,
            label="SRA3",
            width=Decimal("320.00"),
            height=Decimal("450.00"),
            current_stock_level=1000
        )
        
        # Print price
        self.print_price = DigitalPrintPrice.objects.create(
            shop=self.shop,
            machine=self.machine,
            sheet_size="SRA3",
            color_mode="COLOR",
            click_rate=Decimal("15.00"),
            duplex_rate=Decimal("25.00"),
            minimum_order_quantity=1
        )
        
        # Material price
        self.material_price = MaterialPrice.objects.create(
            shop=self.shop,
            material=self.material,
            pricing_method="FIXED",
            selling_price_per_unit=Decimal("20.00")
        )
        
        # Quote and item
        self.quote = Quote.objects.create(
            shop=self.shop,
            user=self.user
        )
        self.item = QuoteItem.objects.create(
            quote=self.quote,
            name="Business Cards",
            quantity=200
        )
        
        self.calculator = QuoteCalculator()
    
    def test_calculate_business_card_cost(self):
        """Test calculating cost for 200 business cards."""
        part = QuoteItemPart.objects.create(
            item=self.item,
            name="Card",
            final_width=Decimal("85.00"),
            final_height=Decimal("55.00"),
            material=self.material,
            preferred_stock=self.stock,
            machine=self.machine,
            print_sides="DUPLEX"
        )
        
        cost = self.calculator.calculate_part_cost(part)
        
        # Imposition: 25 cards per SRA3 sheet
        # Sheets needed: ceil(200/25) = 8 sheets
        # Material: 8 * 20 = 160
        # Print (duplex): 8 * 25 = 200
        # Total: 360
        
        self.assertEqual(part.items_per_sheet, 25)
        self.assertEqual(part.total_sheets_required, 8)
        self.assertEqual(cost, Decimal("360.00"))
    
    def test_calculate_simplex_cost(self):
        """Test simplex printing cost calculation."""
        self.item.quantity = 100
        self.item.save()
        
        part = QuoteItemPart.objects.create(
            item=self.item,
            name="Card",
            final_width=Decimal("85.00"),
            final_height=Decimal("55.00"),
            material=self.material,
            preferred_stock=self.stock,
            machine=self.machine,
            print_sides="SIMPLEX"
        )
        
        cost = self.calculator.calculate_part_cost(part)
        
        # Sheets needed: ceil(100/25) = 4 sheets
        # Material: 4 * 20 = 80
        # Print (simplex): 4 * 15 = 60
        # Total: 140
        
        self.assertEqual(part.total_sheets_required, 4)
        self.assertEqual(cost, Decimal("140.00"))
    
    def test_minimum_order_enforced(self):
        """Test that minimum order quantity is enforced."""
        self.print_price.minimum_order_quantity = 50
        self.print_price.save()
        
        self.item.quantity = 25
        self.item.save()
        
        part = QuoteItemPart.objects.create(
            item=self.item,
            name="Card",
            final_width=Decimal("85.00"),
            final_height=Decimal("55.00"),
            material=self.material,
            preferred_stock=self.stock,
            machine=self.machine,
            print_sides="SIMPLEX"
        )
        
        cost = self.calculator.calculate_part_cost(part)
        
        # Sheets needed: ceil(25/25) = 1 sheet
        # Material: 1 * 20 = 20
        # Print: min(1, 50) = 50 sheets * 15 = 750
        # Total: 770
        
        self.assertEqual(cost, Decimal("770.00"))


class QuoteCalculatorFinishingCostTests(TestCase):
    """Unit tests for QuoteCalculator.calculate_finishing_cost."""
    
    def setUp(self):
        """Set up test data for finishing cost calculations."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.user,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com"
        )
        self.quote = Quote.objects.create(
            shop=self.shop,
            user=self.user
        )
        self.item = QuoteItem.objects.create(
            quote=self.quote,
            name="Test Item",
            quantity=100
        )
        self.calculator = QuoteCalculator()
    
    def test_per_sheet_finishing(self):
        """Test per sheet finishing calculation."""
        finishing_price = FinishingPrice.objects.create(
            shop=self.shop,
            process_name="Matt Lamination",
            category="LAMINATION",
            unit="PER_SHEET",
            price=Decimal("5.00"),
            setup_fee=Decimal("20.00"),
            minimum_order_quantity=1
        )
        finishing_item = QuoteItemFinishing.objects.create(
            item=self.item,
            finishing_price=finishing_price
        )
        
        cost = self.calculator.calculate_finishing_cost(
            finishing_item,
            total_sheets_in_item=10,
            total_quote_qty=100
        )
        
        # 10 sheets * 5 + 20 setup = 70
        self.assertEqual(cost, Decimal("70.00"))
    
    def test_per_piece_finishing(self):
        """Test per piece finishing calculation."""
        finishing_price = FinishingPrice.objects.create(
            shop=self.shop,
            process_name="Saddle Stitching",
            category="BINDING",
            unit="PER_PIECE",
            price=Decimal("10.00"),
            setup_fee=Decimal("0"),
            minimum_order_quantity=1
        )
        finishing_item = QuoteItemFinishing.objects.create(
            item=self.item,
            finishing_price=finishing_price
        )
        
        cost = self.calculator.calculate_finishing_cost(
            finishing_item,
            total_sheets_in_item=50,
            total_quote_qty=100
        )
        
        # 100 pieces * 10 = 1000
        self.assertEqual(cost, Decimal("1000.00"))
    
    def test_per_job_finishing(self):
        """Test per job (flat fee) finishing calculation."""
        finishing_price = FinishingPrice.objects.create(
            shop=self.shop,
            process_name="Cutting",
            category="CUTTING",
            unit="PER_JOB",
            price=Decimal("50.00"),
            setup_fee=Decimal("0"),
            minimum_order_quantity=1
        )
        finishing_item = QuoteItemFinishing.objects.create(
            item=self.item,
            finishing_price=finishing_price
        )
        
        cost = self.calculator.calculate_finishing_cost(
            finishing_item,
            total_sheets_in_item=100,
            total_quote_qty=500
        )
        
        # Flat fee: 50
        self.assertEqual(cost, Decimal("50.00"))
    
    def test_per_batch_finishing(self):
        """Test per batch finishing calculation."""
        finishing_price = FinishingPrice.objects.create(
            shop=self.shop,
            process_name="Creasing",
            category="CREASING",
            unit="PER_BATCH",
            price=Decimal("100.00"),
            batch_size=500,
            setup_fee=Decimal("0"),
            minimum_order_quantity=1
        )
        finishing_item = QuoteItemFinishing.objects.create(
            item=self.item,
            finishing_price=finishing_price
        )
        
        cost = self.calculator.calculate_finishing_cost(
            finishing_item,
            total_sheets_in_item=1200,
            total_quote_qty=100
        )
        
        # ceil(1200/500) = 3 batches * 100 = 300
        self.assertEqual(cost, Decimal("300.00"))
    
    def test_tiered_pricing(self):
        """Test finishing with tiered pricing."""
        finishing_price = FinishingPrice.objects.create(
            shop=self.shop,
            process_name="Binding",
            category="BINDING",
            unit="PER_PIECE",
            price=Decimal("50.00"),  # Base price (tier 1)
            setup_fee=Decimal("0"),
            minimum_order_quantity=1
        )
        
        # Create tiers: 1-50 = 50, 51-100 = 40, 101+ = 30
        PricingTier.objects.create(
            finishing_service=finishing_price,
            min_quantity=1,
            max_quantity=50,
            price_per_unit=Decimal("50.00")
        )
        PricingTier.objects.create(
            finishing_service=finishing_price,
            min_quantity=51,
            max_quantity=100,
            price_per_unit=Decimal("40.00")
        )
        PricingTier.objects.create(
            finishing_service=finishing_price,
            min_quantity=101,
            max_quantity=None,  # Unlimited
            price_per_unit=Decimal("30.00")
        )
        
        finishing_item = QuoteItemFinishing.objects.create(
            item=self.item,
            finishing_price=finishing_price
        )
        
        # Test quantity 75 (falls in 51-100 tier)
        cost = self.calculator.calculate_finishing_cost(
            finishing_item,
            total_sheets_in_item=10,
            total_quote_qty=75
        )
        
        # 75 pieces * 40 = 3000
        self.assertEqual(cost, Decimal("3000.00"))


class QuoteCalculatorTotalTests(TestCase):
    """Integration tests for QuoteCalculator.calculate_quote_total."""
    
    def setUp(self):
        """Set up comprehensive test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.user,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com"
        )
        self.machine = Machine.objects.create(
            shop=self.shop,
            name="Xerox V80",
            type="DIGITAL",
            is_active=True
        )
        self.material = Material.objects.create(
            shop=self.shop,
            name="300gsm Art Card",
            type="SHEET",
            cost_per_unit=Decimal("8.00"),
            unit_type="PER_SHEET",
            is_active=True
        )
        self.stock = MaterialStock.objects.create(
            material=self.material,
            label="SRA3",
            width=Decimal("320.00"),
            height=Decimal("450.00"),
            current_stock_level=1000
        )
        DigitalPrintPrice.objects.create(
            shop=self.shop,
            machine=self.machine,
            sheet_size="SRA3",
            color_mode="COLOR",
            click_rate=Decimal("15.00"),
            duplex_rate=Decimal("25.00"),
            minimum_order_quantity=1
        )
        MaterialPrice.objects.create(
            shop=self.shop,
            material=self.material,
            pricing_method="FIXED",
            selling_price_per_unit=Decimal("20.00")
        )
        self.lamination = FinishingPrice.objects.create(
            shop=self.shop,
            process_name="Matt Lamination",
            category="LAMINATION",
            unit="PER_SIDE",
            price=Decimal("5.00"),
            setup_fee=Decimal("0"),
            minimum_order_quantity=1
        )
        self.calculator = QuoteCalculator()
    
    def test_full_quote_calculation(self):
        """Test full quote calculation - 200 business cards with lamination."""
        quote = Quote.objects.create(
            shop=self.shop,
            user=self.user,
            title="Business Cards"
        )
        item = QuoteItem.objects.create(
            quote=quote,
            name="200 Business Cards",
            quantity=200
        )
        part = QuoteItemPart.objects.create(
            item=item,
            name="Card",
            final_width=Decimal("85.00"),
            final_height=Decimal("55.00"),
            material=self.material,
            preferred_stock=self.stock,
            machine=self.machine,
            print_sides="DUPLEX"
        )
        finishing = QuoteItemFinishing.objects.create(
            item=item,
            finishing_price=self.lamination
        )
        
        # Calculate totals
        total = self.calculator.calculate_quote_total(quote)
        
        # Imposition: 25 cards per SRA3
        # Sheets: ceil(200/25) = 8 sheets
        # Material: 8 * 20 = 160
        # Print (duplex): 8 * 25 = 200
        # Lamination (per side): 8 sheets * 5 = 40
        # Item total: 160 + 200 + 40 = 400
        # Tax (16%): 400 * 0.16 = 64
        # Grand total: 400 + 64 = 464
        
        # Reload from DB
        quote.refresh_from_db()
        item.refresh_from_db()
        part.refresh_from_db()
        
        self.assertEqual(part.items_per_sheet, 25)
        self.assertEqual(part.total_sheets_required, 8)
        self.assertEqual(quote.net_total, Decimal("400.00"))
        self.assertEqual(quote.tax_amount, Decimal("64.00"))
        self.assertEqual(quote.grand_total, Decimal("464.00"))
    
    def test_multi_item_quote(self):
        """Test quote with multiple items."""
        quote = Quote.objects.create(
            shop=self.shop,
            user=self.user
        )
        
        # Item 1: 200 business cards (8 sheets)
        item1 = QuoteItem.objects.create(
            quote=quote,
            name="Business Cards",
            quantity=200
        )
        QuoteItemPart.objects.create(
            item=item1,
            name="Card",
            final_width=Decimal("85.00"),
            final_height=Decimal("55.00"),
            material=self.material,
            preferred_stock=self.stock,
            machine=self.machine,
            print_sides="DUPLEX"
        )
        
        # Item 2: 100 business cards (4 sheets)
        item2 = QuoteItem.objects.create(
            quote=quote,
            name="More Cards",
            quantity=100
        )
        QuoteItemPart.objects.create(
            item=item2,
            name="Card",
            final_width=Decimal("85.00"),
            final_height=Decimal("55.00"),
            material=self.material,
            preferred_stock=self.stock,
            machine=self.machine,
            print_sides="SIMPLEX"
        )
        
        self.calculator.calculate_quote_total(quote)
        
        quote.refresh_from_db()
        
        # Item 1: Material 160 + Print 200 = 360
        # Item 2: Material 80 + Print 60 = 140 (simplex)
        # Net: 500
        # Tax: 80
        # Grand: 580
        
        self.assertEqual(quote.net_total, Decimal("500.00"))
        self.assertEqual(quote.grand_total, Decimal("580.00"))


# =============================================================================
# API Tests
# =============================================================================


class QuoteAPITests(APITestCase):
    """API tests for quote endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
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
        self.quote = Quote.objects.create(
            shop=self.shop,
            user=self.user,
            title="Test Quote"
        )
        self.client = APIClient()
    
    def test_quote_list_requires_auth(self):
        """Test quote list requires authentication."""
        url = f"/api/shops/{self.shop.slug}/quotes/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_shop_owner_can_list_quotes(self):
        """Test shop owner can list all quotes."""
        self.client.force_authenticate(user=self.user)
        url = f"/api/shops/{self.shop.slug}/quotes/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_my_quotes_endpoint(self):
        """Test customers can see their own quotes."""
        # Create a quote for another user
        Quote.objects.create(
            shop=self.shop,
            user=self.other_user,
            title="Other User Quote"
        )
        
        self.client.force_authenticate(user=self.user)
        url = "/api/my-quotes/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see own quote
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Quote")
    
    def test_quote_status_update(self):
        """Test updating quote status."""
        self.client.force_authenticate(user=self.user)
        url = f"/api/shops/{self.shop.slug}/quotes/{self.quote.id}/"
        
        response = self.client.patch(url, {"status": "SENT"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, "SENT")


class ProductTemplateAPITests(APITestCase):
    """API tests for product template endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
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
        self.template = ProductTemplate.objects.create(
            shop=self.shop,
            name="Standard Biz Card",
            defaults={"final_width": 85, "final_height": 55}
        )
        self.client = APIClient()
    
    def test_template_list_requires_auth(self):
        """Test product template list requires authentication."""
        url = f"/api/shops/{self.shop.slug}/product-templates/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_shop_owner_can_list_templates(self):
        """Test shop owner can list templates."""
        self.client.force_authenticate(user=self.user)
        url = f"/api/shops/{self.shop.slug}/product-templates/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_create_product_template(self):
        """Test creating a new product template."""
        self.client.force_authenticate(user=self.user)
        url = f"/api/shops/{self.shop.slug}/product-templates/"
        data = {
            "name": "A5 Flyer",
            "description": "Single sided flyer",
            "defaults": {"final_width": 148, "final_height": 210}
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProductTemplate.objects.filter(shop=self.shop).count(), 2)
    
    def test_unauthorized_user_cannot_create(self):
        """Test unauthorized user cannot create templates."""
        self.client.force_authenticate(user=self.other_user)
        url = f"/api/shops/{self.shop.slug}/product-templates/"
        data = {
            "name": "Unauthorized Template",
            "defaults": {}
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CustomerQuoteRequestAPITests(APITestCase):
    """API tests for customer quote request endpoint."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="shop@example.com",
            password="testpass123"
        )
        self.customer = User.objects.create_user(
            email="customer@example.com",
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
        self.client = APIClient()
    
    def test_anonymous_can_request_quote(self):
        """Test anonymous users can request quotes."""
        url = f"/api/shops/{self.shop.slug}/quote-request/"
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+254700000000",
            "product_name": "Business Cards",
            "quantity": 500,
            "notes": "Double sided, matte lamination"
        }
        response = self.client.post(url, data, format="json")
        # Should succeed (either 200 or 201 depending on implementation)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
    
    def test_authenticated_customer_can_request_quote(self):
        """Test authenticated customers can request quotes."""
        self.client.force_authenticate(user=self.customer)
        url = f"/api/shops/{self.shop.slug}/quote-request/"
        data = {
            "product_name": "Flyers",
            "quantity": 1000,
        }
        response = self.client.post(url, data, format="json")
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
