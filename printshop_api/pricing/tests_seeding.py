"""
Tests for pricing templates and shop seeding.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from django.contrib.auth import get_user_model

from shops.models import Shop
from inventory.models import Machine
from pricing.models import (
    PrintingPrice,
    PaperPrice,
    MaterialPrice,
    FinishingService,
    DefaultPrintingPriceTemplate,
    DefaultPaperPriceTemplate,
    DefaultMaterialPriceTemplate,
    DefaultFinishingServiceTemplate,
)
from pricing.services.seeding import seed_shop_pricing

User = get_user_model()


class SeedingServiceTests(TestCase):
    """Tests for seed_shop_pricing service."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
        )
        self.shop = Shop.objects.create(
            owner=self.user,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 St",
            city="Nairobi",
            zip_code="00100",
            country="Kenya",
        )
        self.machine = Machine.objects.create(
            shop=self.shop,
            name="Xerox V80",
            machine_type="DIGITAL",
            is_active=True,
        )
        # Create templates
        DefaultPrintingPriceTemplate.objects.create(
            machine_category="DIGITAL",
            sheet_size="A4",
            color_mode="COLOR",
            selling_price_per_side=Decimal("15.00"),
            selling_price_duplex_per_sheet=Decimal("25.00"),
        )
        DefaultPaperPriceTemplate.objects.create(
            sheet_size="A4",
            paper_type="GLOSS",
            gsm=130,
            selling_price=Decimal("10.00"),
            buying_price=Decimal("6.00"),
        )
        DefaultMaterialPriceTemplate.objects.create(
            material_type="VINYL",
            unit="SQM",
            selling_price=Decimal("500.00"),
            buying_price=Decimal("300.00"),
        )
        DefaultFinishingServiceTemplate.objects.create(
            name="Matt Lamination A3",
            unit_type="PER_SHEET",
            selling_price=Decimal("5.00"),
            buying_price=Decimal("2.00"),
        )

    def test_seed_creates_missing_rows(self):
        """Seeding creates rows that don't exist."""
        result = seed_shop_pricing(self.shop)
        self.assertEqual(result["printing"]["created"], 1)
        self.assertEqual(result["paper"]["created"], 1)
        self.assertEqual(result["material"]["created"], 1)
        self.assertEqual(result["finishing"]["created"], 1)

        # Verify created rows
        pp = PrintingPrice.objects.get(shop=self.shop, machine=self.machine, sheet_size="A4", color_mode="COLOR")
        self.assertEqual(pp.selling_price_per_side, Decimal("15.00"))
        self.assertEqual(pp.selling_price_duplex_per_sheet, Decimal("25.00"))
        self.assertTrue(pp.is_default_seeded)
        self.assertTrue(pp.needs_review)

    def test_seed_idempotent_no_overwrite(self):
        """Second seed without overwrite does not create duplicates."""
        seed_shop_pricing(self.shop)
        result = seed_shop_pricing(self.shop)
        self.assertEqual(result["printing"]["created"], 0)
        self.assertEqual(result["paper"]["created"], 0)
        self.assertEqual(result["material"]["created"], 0)
        self.assertEqual(result["finishing"]["created"], 0)

        self.assertEqual(PrintingPrice.objects.filter(shop=self.shop).count(), 1)
        self.assertEqual(PaperPrice.objects.filter(shop=self.shop).count(), 1)
        self.assertEqual(MaterialPrice.objects.filter(shop=self.shop).count(), 1)
        self.assertEqual(FinishingService.objects.filter(shop=self.shop).count(), 1)

    def test_seed_with_machine_ids_filters(self):
        """Seeding with machine_ids only seeds those machines."""
        machine2 = Machine.objects.create(
            shop=self.shop,
            name="Canon Press",
            machine_type="DIGITAL",
            is_active=True,
        )
        result = seed_shop_pricing(self.shop, machine_ids=[self.machine.id])
        # Only one machine, so one printing price
        self.assertEqual(result["printing"]["created"], 1)
        self.assertEqual(PrintingPrice.objects.filter(shop=self.shop, machine=self.machine).count(), 1)
        self.assertEqual(PrintingPrice.objects.filter(shop=self.shop, machine=machine2).count(), 0)

    def test_overwrite_updates_seeded_needs_review_only(self):
        """Overwrite only updates rows where is_default_seeded and needs_review."""
        seed_shop_pricing(self.shop)
        pp = PrintingPrice.objects.get(shop=self.shop, machine=self.machine, sheet_size="A4", color_mode="COLOR")
        pp.selling_price_per_side = Decimal("20.00")
        pp.save()

        # Update template
        tpl = DefaultPrintingPriceTemplate.objects.get(machine_category="DIGITAL", sheet_size="A4", color_mode="COLOR")
        tpl.selling_price_per_side = Decimal("18.00")
        tpl.save()

        # Overwrite - should update because needs_review is still True
        result = seed_shop_pricing(self.shop, overwrite=True)
        self.assertEqual(result["printing"]["updated"], 1)
        pp.refresh_from_db()
        self.assertEqual(pp.selling_price_per_side, Decimal("18.00"))

    def test_overwrite_skips_needs_review_false(self):
        """Overwrite does NOT update rows where needs_review=False."""
        seed_shop_pricing(self.shop)
        pp = PrintingPrice.objects.get(shop=self.shop, machine=self.machine, sheet_size="A4", color_mode="COLOR")
        pp.needs_review = False
        pp.selling_price_per_side = Decimal("22.00")
        pp.save()

        tpl = DefaultPrintingPriceTemplate.objects.get(machine_category="DIGITAL", sheet_size="A4", color_mode="COLOR")
        tpl.selling_price_per_side = Decimal("12.00")
        tpl.save()

        result = seed_shop_pricing(self.shop, overwrite=True)
        self.assertEqual(result["printing"]["updated"], 0)
        pp.refresh_from_db()
        self.assertEqual(pp.selling_price_per_side, Decimal("22.00"))


class NeedsReviewToggleTests(APITestCase):
    """Tests that PATCH/PUT sets needs_review=False."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
        )
        self.shop = Shop.objects.create(
            owner=self.user,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 St",
            city="Nairobi",
            zip_code="00100",
            country="Kenya",
        )
        self.machine = Machine.objects.create(
            shop=self.shop,
            name="Xerox V80",
            machine_type="DIGITAL",
            is_active=True,
        )
        self.print_price = PrintingPrice.objects.create(
            shop=self.shop,
            machine=self.machine,
            sheet_size="A4",
            color_mode="COLOR",
            selling_price_per_side=Decimal("15.00"),
            is_default_seeded=True,
            needs_review=True,
        )
        self.client = APIClient()

    def test_patch_sets_needs_review_false(self):
        """PATCH update sets needs_review to False."""
        self.client.force_authenticate(user=self.user)
        url = f"/api/shops/{self.shop.slug}/pricing/printing/{self.print_price.id}/"
        self.client.patch(url, {"selling_price_per_side": "16.00"}, format="json")
        self.print_price.refresh_from_db()
        self.assertFalse(self.print_price.needs_review)

    def test_put_sets_needs_review_false(self):
        """PUT update sets needs_review to False."""
        self.client.force_authenticate(user=self.user)
        url = f"/api/shops/{self.shop.slug}/pricing/printing/{self.print_price.id}/"
        data = {
            "machine": self.machine.id,
            "sheet_size": "A4",
            "color_mode": "COLOR",
            "selling_price_per_side": "17.00",
            "is_active": True,
        }
        self.client.put(url, data, format="json")
        self.print_price.refresh_from_db()
        self.assertFalse(self.print_price.needs_review)
