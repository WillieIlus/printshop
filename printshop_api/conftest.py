# conftest.py - Shared pytest fixtures for all apps

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model

from shops.models import Shop, ShopMember
from inventory.models import Machine, Material, MaterialStock
from pricing.models import (
    DigitalPrintPrice, 
    MaterialPrice, 
    FinishingPrice, 
    PaperGSMPrice
)
from templates.models import TemplateCategory, PrintTemplate, TemplateFinishing
from quotes.models import Quote, QuoteItem, QuoteItemPart, ProductTemplate


User = get_user_model()


# =============================================================================
# User Fixtures
# =============================================================================

@pytest.fixture
def user(db):
    """Create a regular user."""
    return User.objects.create_user(
        email="testuser@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User"
    )


@pytest.fixture
def user2(db):
    """Create a second user for permission tests."""
    return User.objects.create_user(
        email="testuser2@example.com",
        password="testpass123",
        first_name="Test2",
        last_name="User2"
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
        first_name="Admin",
        last_name="User"
    )


# =============================================================================
# Shop Fixtures
# =============================================================================

@pytest.fixture
def shop(db, user):
    """Create a test shop."""
    return Shop.objects.create(
        owner=user,
        name="Test Print Shop",
        slug="test-print-shop",
        description="A test print shop",
        business_email="shop@example.com",
        phone_number="+254712345678",
        address_line="123 Test Street",
        city="Nairobi",
        state="Nairobi County",
        zip_code="00100",
        country="Kenya",
        is_verified=True,
        is_active=True
    )


@pytest.fixture
def shop2(db, user2):
    """Create a second shop for permission tests."""
    return Shop.objects.create(
        owner=user2,
        name="Another Print Shop",
        slug="another-print-shop",
        description="Another test shop",
        business_email="shop2@example.com",
        address_line="456 Other Street",
        city="Mombasa",
        zip_code="80100",
        country="Kenya",
        is_active=True
    )


@pytest.fixture
def shop_member(db, shop, user2):
    """Create a shop member (staff)."""
    return ShopMember.objects.create(
        shop=shop,
        user=user2,
        role=ShopMember.Role.STAFF,
        is_active=True
    )


@pytest.fixture
def shop_manager(db, shop, user2):
    """Create a shop manager."""
    return ShopMember.objects.create(
        shop=shop,
        user=user2,
        role=ShopMember.Role.MANAGER,
        is_active=True
    )


# =============================================================================
# Inventory Fixtures
# =============================================================================

@pytest.fixture
def machine(db, shop):
    """Create a test machine."""
    return Machine.objects.create(
        shop=shop,
        name="Xerox V80",
        type="DIGITAL",
        is_active=True
    )


@pytest.fixture
def material(db, shop):
    """Create a test material."""
    return Material.objects.create(
        shop=shop,
        name="300gsm Art Card",
        type="SHEET",
        cost_per_unit=Decimal("8.00"),
        unit_type="PER_SHEET",
        is_active=True
    )


@pytest.fixture
def material_stock(db, material):
    """Create material stock (SRA3 size)."""
    return MaterialStock.objects.create(
        material=material,
        label="SRA3",
        width=Decimal("320"),
        height=Decimal("450"),
        current_stock_level=1000
    )


# =============================================================================
# Pricing Fixtures
# =============================================================================

@pytest.fixture
def digital_print_price(db, shop, machine):
    """Create a digital print price."""
    return DigitalPrintPrice.objects.create(
        shop=shop,
        machine=machine,
        sheet_size="SRA3",
        color_mode="COLOR",
        click_rate=Decimal("15.00"),
        duplex_rate=Decimal("25.00"),
        minimum_order_quantity=1,
        is_active=True
    )


@pytest.fixture
def digital_print_price_a3(db, shop, machine):
    """Create A3 digital print price."""
    return DigitalPrintPrice.objects.create(
        shop=shop,
        machine=machine,
        sheet_size="A3",
        color_mode="COLOR",
        click_rate=Decimal("15.00"),
        duplex_rate=Decimal("25.00"),
        minimum_order_quantity=1,
        is_active=True
    )


@pytest.fixture
def material_price(db, shop, material):
    """Create a material price."""
    return MaterialPrice.objects.create(
        shop=shop,
        material=material,
        pricing_method="FIXED",
        selling_price_per_unit=Decimal("20.00"),
        is_active=True
    )


@pytest.fixture
def finishing_price(db, shop):
    """Create a finishing price (lamination)."""
    return FinishingPrice.objects.create(
        shop=shop,
        process_name="Matt Lamination SRA3",
        description="Matt lamination for SRA3 sheets",
        category="LAMINATION",
        unit="PER_SIDE",
        price=Decimal("5.00"),
        setup_fee=Decimal("0"),
        minimum_order_quantity=1,
        is_mandatory=False,
        is_default_selected=False,
        is_active=True
    )


@pytest.fixture
def mandatory_finishing(db, shop):
    """Create a mandatory finishing price."""
    return FinishingPrice.objects.create(
        shop=shop,
        process_name="Cutting",
        description="Standard cutting",
        category="CUTTING",
        unit="PER_JOB",
        price=Decimal("50.00"),
        is_mandatory=True,
        is_active=True
    )


@pytest.fixture
def paper_gsm_price(db, shop):
    """Create paper GSM prices."""
    prices = []
    gsm_prices = [
        (130, Decimal("10.00")),
        (150, Decimal("15.00")),
        (200, Decimal("20.00")),
        (300, Decimal("30.00")),
    ]
    for gsm, price in gsm_prices:
        prices.append(PaperGSMPrice.objects.create(
            shop=shop,
            sheet_size="A3",
            gsm=gsm,
            paper_type="Gloss",
            price_per_sheet=price,
            cost_per_sheet=price * Decimal("0.6"),
            is_active=True
        ))
    return prices


@pytest.fixture
def paper_gsm_price_300(db, shop):
    """Create a single 300gsm paper price."""
    return PaperGSMPrice.objects.create(
        shop=shop,
        sheet_size="A3",
        gsm=300,
        paper_type="Gloss",
        price_per_sheet=Decimal("30.00"),
        cost_per_sheet=Decimal("18.00"),
        is_active=True
    )


# =============================================================================
# Template Fixtures
# =============================================================================

@pytest.fixture
def template_category(db):
    """Create a template category."""
    return TemplateCategory.objects.create(
        name="Business Cards",
        slug="business-cards",
        description="Professional business cards",
        display_order=1,
        is_active=True
    )


@pytest.fixture
def print_template(db, template_category, shop):
    """Create a print template."""
    return PrintTemplate.objects.create(
        shop=shop,
        title="Premium Business Cards",
        slug="premium-business-cards",
        category=template_category,
        description="High quality business cards on premium stock",
        base_price=Decimal("1200.00"),
        min_quantity=100,
        final_width=Decimal("90"),
        final_height=Decimal("55"),
        default_gsm=300,
        default_print_sides="DUPLEX",
        dimensions_label="90 × 55 mm",
        weight_label="300gsm",
        is_popular=True,
        is_active=True
    )


@pytest.fixture
def template_finishing(db, print_template):
    """Create template finishing options."""
    mandatory = TemplateFinishing.objects.create(
        template=print_template,
        name="Matt Lamination",
        description="Protective matt lamination",
        is_mandatory=True,
        is_default=True,
        price_adjustment=Decimal("0"),
        display_order=1
    )
    optional = TemplateFinishing.objects.create(
        template=print_template,
        name="Spot UV",
        description="Glossy spot UV coating",
        is_mandatory=False,
        is_default=False,
        price_adjustment=Decimal("200.00"),
        display_order=2
    )
    return [mandatory, optional]


# =============================================================================
# Quote Fixtures
# =============================================================================

@pytest.fixture
def quote(db, shop, user):
    """Create a test quote."""
    return Quote.objects.create(
        shop=shop,
        user=user,
        title="Test Business Cards",
        status=Quote.Status.DRAFT
    )


@pytest.fixture
def quote_item(db, quote):
    """Create a quote item."""
    return QuoteItem.objects.create(
        quote=quote,
        name="Business Cards",
        quantity=200
    )


@pytest.fixture
def quote_item_part(db, quote_item, material, material_stock, machine):
    """Create a quote item part."""
    return QuoteItemPart.objects.create(
        item=quote_item,
        name="Main Card",
        final_width=Decimal("85"),
        final_height=Decimal("55"),
        material=material,
        preferred_stock=material_stock,
        machine=machine,
        print_sides="DUPLEX"
    )


@pytest.fixture
def product_template(db, shop):
    """Create a shop product template."""
    return ProductTemplate.objects.create(
        shop=shop,
        name="Standard Business Card",
        description="Our most popular business card preset",
        defaults={
            "final_width": 85,
            "final_height": 55,
            "print_sides": "DUPLEX"
        },
        is_active=True
    )


# =============================================================================
# API Client Fixtures
# =============================================================================

@pytest.fixture
def api_client():
    """Return a DRF API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an admin authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client
