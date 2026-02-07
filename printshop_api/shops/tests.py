# shops/tests.py

from decimal import Decimal
from datetime import time
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APITestCase, APIClient, APIRequestFactory

from django.contrib.auth import get_user_model

from shops.models import Shop, ShopMember, OpeningHours, ShopSocialLink, ShopClaim
from shops.permissions import (
    IsShopOwner,
    IsShopOwnerOrReadOnly,
    IsShopMember,
    IsShopManagerOrOwner,
    CanManageShopMembers,
    IsClaimOwner,
    IsAdminOrClaimOwner,
)


User = get_user_model()


# =============================================================================
# Model Tests
# =============================================================================


class ShopModelTests(TestCase):
    """Unit tests for Shop model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
    
    def test_shop_creation(self):
        """Test basic shop creation."""
        shop = Shop.objects.create(
            owner=self.user,
            name="Test Print Shop",
            slug="test-print-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100",
            country="Kenya"
        )
        self.assertEqual(str(shop), "Test Print Shop")
        self.assertTrue(shop.is_active)
        self.assertFalse(shop.is_verified)
    
    def test_unique_slug_constraint(self):
        """Test unique slug constraint."""
        Shop.objects.create(
            owner=self.user,
            name="Shop One",
            slug="unique-slug",
            business_email="shop1@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100"
        )
        with self.assertRaises(IntegrityError):
            Shop.objects.create(
                owner=self.user,
                name="Shop Two",
                slug="unique-slug",  # Duplicate
                business_email="shop2@example.com",
                address_line="456 Other St",
                city="Mombasa",
                zip_code="80100"
            )
    
    def test_gps_coordinates(self):
        """Test GPS coordinate precision."""
        shop = Shop.objects.create(
            owner=self.user,
            name="GPS Shop",
            slug="gps-shop",
            business_email="gps@example.com",
            address_line="GPS Location",
            city="Nairobi",
            zip_code="00100",
            latitude=Decimal("-1.286389"),
            longitude=Decimal("36.817223")
        )
        self.assertEqual(shop.latitude, Decimal("-1.286389"))
        self.assertEqual(shop.longitude, Decimal("36.817223"))


class ShopMemberModelTests(TestCase):
    """Unit tests for ShopMember model."""
    
    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100"
        )
    
    def test_member_creation(self):
        """Test basic member creation."""
        member = ShopMember.objects.create(
            shop=self.shop,
            user=self.staff,
            role=ShopMember.Role.STAFF
        )
        self.assertEqual(str(member), f"{self.staff} - Test Shop (Staff)")
        self.assertTrue(member.is_active)
    
    def test_role_choices(self):
        """Test all role choices."""
        roles = [
            (ShopMember.Role.OWNER, "Owner"),
            (ShopMember.Role.MANAGER, "Manager"),
            (ShopMember.Role.STAFF, "Staff"),
            (ShopMember.Role.DESIGNER, "Designer"),
        ]
        for i, (role_value, role_label) in enumerate(roles):
            member = ShopMember(
                shop=self.shop,
                user=User.objects.create_user(
                    email=f"roletest{i}_{role_value.lower()}@example.com",
                    password="test"
                ),
                role=role_value
            )
            self.assertEqual(member.get_role_display(), role_label)
    
    def test_unique_membership_constraint(self):
        """Test user cannot be added to same shop twice."""
        ShopMember.objects.create(
            shop=self.shop,
            user=self.staff,
            role=ShopMember.Role.STAFF
        )
        with self.assertRaises(IntegrityError):
            ShopMember.objects.create(
                shop=self.shop,
                user=self.staff,  # Same user
                role=ShopMember.Role.DESIGNER  # Different role doesn't matter
            )


class OpeningHoursModelTests(TestCase):
    """Unit tests for OpeningHours model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.user,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100"
        )
    
    def test_opening_hours_creation(self):
        """Test basic opening hours creation."""
        hours = OpeningHours.objects.create(
            shop=self.shop,
            weekday=OpeningHours.Weekday.MONDAY,
            from_hour=time(9, 0),
            to_hour=time(17, 0),
            is_closed=False
        )
        self.assertEqual(
            str(hours),
            "Test Shop: Monday 09:00:00 - 17:00:00"
        )
    
    def test_closed_day(self):
        """Test closed day representation."""
        hours = OpeningHours.objects.create(
            shop=self.shop,
            weekday=OpeningHours.Weekday.SUNDAY,
            is_closed=True
        )
        self.assertEqual(str(hours), "Test Shop: Sunday (Closed)")
    
    def test_validation_closing_after_opening(self):
        """Test validation that closing is after opening."""
        hours = OpeningHours(
            shop=self.shop,
            weekday=OpeningHours.Weekday.TUESDAY,
            from_hour=time(17, 0),  # Later
            to_hour=time(9, 0),      # Earlier - invalid
            is_closed=False
        )
        with self.assertRaises(ValidationError):
            hours.clean()
    
    def test_validation_times_required_if_open(self):
        """Test validation that times are required if not closed."""
        hours = OpeningHours(
            shop=self.shop,
            weekday=OpeningHours.Weekday.WEDNESDAY,
            is_closed=False
            # No from_hour or to_hour
        )
        with self.assertRaises(ValidationError):
            hours.clean()


class ShopSocialLinkModelTests(TestCase):
    """Unit tests for ShopSocialLink model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.user,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100"
        )
    
    def test_social_link_creation(self):
        """Test basic social link creation."""
        link = ShopSocialLink.objects.create(
            shop=self.shop,
            platform=ShopSocialLink.Platform.INSTAGRAM,
            url="https://instagram.com/testshop",
            username="testshop"
        )
        self.assertEqual(str(link), "Instagram - Test Shop")
    
    def test_unique_platform_constraint(self):
        """Test one link per platform per shop."""
        ShopSocialLink.objects.create(
            shop=self.shop,
            platform=ShopSocialLink.Platform.FACEBOOK,
            url="https://facebook.com/testshop"
        )
        with self.assertRaises(IntegrityError):
            ShopSocialLink.objects.create(
                shop=self.shop,
                platform=ShopSocialLink.Platform.FACEBOOK,  # Duplicate platform
                url="https://facebook.com/testshop2"
            )


class ShopClaimModelTests(TestCase):
    """Unit tests for ShopClaim model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="claimant@example.com",
            password="testpass123"
        )
    
    def test_claim_creation(self):
        """Test basic claim creation."""
        claim = ShopClaim.objects.create(
            user=self.user,
            business_name="New Print Shop",
            business_email="newshop@example.com"
        )
        self.assertEqual(claim.status, ShopClaim.Status.PENDING)
        self.assertIsNotNone(claim.token)  # UUID auto-generated
    
    def test_claim_str_representation(self):
        """Test claim string representation."""
        claim = ShopClaim.objects.create(
            user=self.user,
            business_name="Claim Test Shop",
            business_email="claim@example.com"
        )
        expected = f"Claim by {self.user} for 'Claim Test Shop' (Pending)"
        self.assertEqual(str(claim), expected)


# =============================================================================
# Permission Tests
# =============================================================================


class MockRequest:
    """Simple mock request for permission testing."""
    def __init__(self, user, method="GET"):
        self.user = user
        self.method = method


class IsShopOwnerPermissionTests(TestCase):
    """Unit tests for IsShopOwner permission."""
    
    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100"
        )
        self.permission = IsShopOwner()
    
    def test_owner_has_permission(self):
        """Test owner has permission on shop object."""
        request = MockRequest(self.owner)
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.shop)
        )
    
    def test_non_owner_denied(self):
        """Test non-owner is denied permission."""
        request = MockRequest(self.other_user)
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.shop)
        )
    
    def test_owner_has_permission_on_related_object(self):
        """Test owner has permission on objects with shop FK."""
        member = ShopMember.objects.create(
            shop=self.shop,
            user=self.other_user,
            role=ShopMember.Role.STAFF
        )
        request = MockRequest(self.owner)
        self.assertTrue(
            self.permission.has_object_permission(request, None, member)
        )


class IsShopOwnerOrReadOnlyPermissionTests(TestCase):
    """Unit tests for IsShopOwnerOrReadOnly permission."""
    
    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100"
        )
        self.permission = IsShopOwnerOrReadOnly()
    
    def test_anyone_can_read(self):
        """Test anyone can read (GET request)."""
        request = MockRequest(self.other_user, method="GET")
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.shop)
        )
    
    def test_owner_can_write(self):
        """Test owner can write (POST/PUT/PATCH)."""
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            request = MockRequest(self.owner, method=method)
            self.assertTrue(
                self.permission.has_object_permission(request, None, self.shop)
            )
    
    def test_non_owner_cannot_write(self):
        """Test non-owner cannot write."""
        request = MockRequest(self.other_user, method="PATCH")
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.shop)
        )


class IsShopMemberPermissionTests(TestCase):
    """Unit tests for IsShopMember permission."""
    
    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="testpass123"
        )
        self.non_member = User.objects.create_user(
            email="nonmember@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100"
        )
        ShopMember.objects.create(
            shop=self.shop,
            user=self.staff,
            role=ShopMember.Role.STAFF,
            is_active=True
        )
        self.permission = IsShopMember()
    
    def test_owner_has_access(self):
        """Test owner always has member access."""
        request = MockRequest(self.owner)
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.shop)
        )
    
    def test_active_member_has_access(self):
        """Test active member has access."""
        request = MockRequest(self.staff)
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.shop)
        )
    
    def test_non_member_denied(self):
        """Test non-member is denied."""
        request = MockRequest(self.non_member)
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.shop)
        )
    
    def test_inactive_member_denied(self):
        """Test inactive member is denied."""
        member = ShopMember.objects.get(shop=self.shop, user=self.staff)
        member.is_active = False
        member.save()
        
        request = MockRequest(self.staff)
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.shop)
        )


class IsShopManagerOrOwnerPermissionTests(TestCase):
    """Unit tests for IsShopManagerOrOwner permission."""
    
    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="testpass123"
        )
        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100"
        )
        ShopMember.objects.create(
            shop=self.shop,
            user=self.manager,
            role=ShopMember.Role.MANAGER,
            is_active=True
        )
        ShopMember.objects.create(
            shop=self.shop,
            user=self.staff,
            role=ShopMember.Role.STAFF,
            is_active=True
        )
        self.permission = IsShopManagerOrOwner()
    
    def test_owner_has_access(self):
        """Test owner has access."""
        request = MockRequest(self.owner)
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.shop)
        )
    
    def test_manager_has_access(self):
        """Test manager has access."""
        request = MockRequest(self.manager)
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.shop)
        )
    
    def test_staff_denied(self):
        """Test regular staff is denied."""
        request = MockRequest(self.staff)
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.shop)
        )


class CanManageShopMembersPermissionTests(TestCase):
    """Unit tests for CanManageShopMembers permission."""
    
    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="testpass123"
        )
        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="testpass123"
        )
        self.designer = User.objects.create_user(
            email="designer@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100"
        )
        self.manager_member = ShopMember.objects.create(
            shop=self.shop,
            user=self.manager,
            role=ShopMember.Role.MANAGER,
            is_active=True
        )
        self.staff_member = ShopMember.objects.create(
            shop=self.shop,
            user=self.staff,
            role=ShopMember.Role.STAFF,
            is_active=True
        )
        self.designer_member = ShopMember.objects.create(
            shop=self.shop,
            user=self.designer,
            role=ShopMember.Role.DESIGNER,
            is_active=True
        )
        self.permission = CanManageShopMembers()
    
    def test_owner_can_manage_anyone(self):
        """Test owner can manage all members."""
        request = MockRequest(self.owner)
        
        # Can manage manager
        self.assertTrue(
            self.permission.has_object_permission(
                request, None, self.manager_member
            )
        )
        # Can manage staff
        self.assertTrue(
            self.permission.has_object_permission(
                request, None, self.staff_member
            )
        )
    
    def test_manager_can_manage_staff(self):
        """Test manager can manage staff and designers."""
        request = MockRequest(self.manager)
        
        # Can manage staff
        self.assertTrue(
            self.permission.has_object_permission(
                request, None, self.staff_member
            )
        )
        # Can manage designer
        self.assertTrue(
            self.permission.has_object_permission(
                request, None, self.designer_member
            )
        )
    
    def test_manager_cannot_manage_other_manager(self):
        """Test manager cannot manage other managers."""
        other_manager = User.objects.create_user(
            email="othermanager@example.com",
            password="testpass123"
        )
        other_manager_member = ShopMember.objects.create(
            shop=self.shop,
            user=other_manager,
            role=ShopMember.Role.MANAGER,
            is_active=True
        )
        
        request = MockRequest(self.manager)
        self.assertFalse(
            self.permission.has_object_permission(
                request, None, other_manager_member
            )
        )


# =============================================================================
# API Tests
# =============================================================================


class ShopAPITests(APITestCase):
    """API tests for shop endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="Test Print Shop",
            slug="test-print-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100",
            is_active=True,
            is_verified=True
        )
        self.inactive_shop = Shop.objects.create(
            owner=self.owner,
            name="Inactive Shop",
            slug="inactive-shop",
            business_email="inactive@example.com",
            address_line="456 Other St",
            city="Mombasa",
            zip_code="80100",
            is_active=False
        )
        self.client = APIClient()
    
    def test_shop_list_public(self):
        """Test shop list is publicly accessible."""
        url = "/api/shops/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_shop_list_filters_inactive(self):
        """Test inactive shops are filtered by default."""
        url = "/api/shops/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [s["slug"] for s in response.data]
        self.assertIn("test-print-shop", slugs)
        self.assertNotIn("inactive-shop", slugs)
    
    def test_shop_detail_by_slug(self):
        """Test shop detail retrieval by slug."""
        url = f"/api/shops/{self.shop.slug}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Print Shop")
    
    def test_shop_update_requires_auth(self):
        """Test shop update requires authentication."""
        url = f"/api/shops/{self.shop.slug}/"
        response = self.client.patch(url, {"name": "Updated Name"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_owner_can_update_shop(self):
        """Test owner can update their shop."""
        self.client.force_authenticate(user=self.owner)
        url = f"/api/shops/{self.shop.slug}/"
        response = self.client.patch(
            url,
            {"name": "Updated Shop Name"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.name, "Updated Shop Name")
    
    def test_non_owner_cannot_update_shop(self):
        """Test non-owner cannot update shop."""
        self.client.force_authenticate(user=self.other_user)
        url = f"/api/shops/{self.shop.slug}/"
        response = self.client.patch(
            url,
            {"name": "Hacked Name"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_search_shops_by_city(self):
        """Test searching shops by city."""
        url = "/api/shops/?city=Nairobi"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["slug"], "test-print-shop")


class ShopMemberAPITests(APITestCase):
    """API tests for shop member management."""
    
    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="testpass123"
        )
        self.new_user = User.objects.create_user(
            email="newuser@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100",
            is_active=True
        )
        self.staff_member = ShopMember.objects.create(
            shop=self.shop,
            user=self.staff,
            role=ShopMember.Role.STAFF,
            is_active=True
        )
        self.client = APIClient()
    
    def test_list_members_requires_auth(self):
        """Test listing members requires authentication."""
        url = f"/api/shops/{self.shop.slug}/members/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_owner_can_list_members(self):
        """Test owner can list shop members."""
        self.client.force_authenticate(user=self.owner)
        url = f"/api/shops/{self.shop.slug}/members/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_owner_can_add_member(self):
        """Test owner can add new member."""
        self.client.force_authenticate(user=self.owner)
        url = f"/api/shops/{self.shop.slug}/members/"
        data = {
            "user": self.new_user.id,
            "role": "DESIGNER"
        }
        response = self.client.post(url, data, format="json")
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
    
    def test_staff_cannot_add_member(self):
        """Test staff cannot add members."""
        self.client.force_authenticate(user=self.staff)
        url = f"/api/shops/{self.shop.slug}/members/"
        data = {
            "user": self.new_user.id,
            "role": "DESIGNER"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OpeningHoursAPITests(APITestCase):
    """API tests for opening hours management."""
    
    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123"
        )
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="Test Shop",
            slug="test-shop",
            business_email="shop@example.com",
            address_line="123 Main St",
            city="Nairobi",
            zip_code="00100",
            is_active=True
        )
        OpeningHours.objects.create(
            shop=self.shop,
            weekday=1,  # Monday
            from_hour=time(9, 0),
            to_hour=time(17, 0)
        )
        self.client = APIClient()
    
    def test_public_can_view_hours(self):
        """Test public can view opening hours."""
        url = f"/api/shops/{self.shop.slug}/opening-hours/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_owner_can_update_hours(self):
        """Test owner can update opening hours."""
        self.client.force_authenticate(user=self.owner)
        hours = OpeningHours.objects.first()
        url = f"/api/shops/{self.shop.slug}/opening-hours/{hours.id}/"
        response = self.client.patch(
            url,
            {"from_hour": "08:00"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_non_owner_cannot_update_hours(self):
        """Test non-owner cannot update opening hours."""
        self.client.force_authenticate(user=self.other_user)
        hours = OpeningHours.objects.first()
        url = f"/api/shops/{self.shop.slug}/opening-hours/{hours.id}/"
        response = self.client.patch(
            url,
            {"from_hour": "08:00"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
