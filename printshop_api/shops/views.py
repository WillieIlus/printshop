# shops/views.py

"""
Django REST Framework views for the shops app.
"""

from __future__ import annotations

from math import cos, radians  # Move this import to the top

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import OpeningHours, Shop, ShopClaim, ShopMember, ShopSocialLink
from .permissions import (
    CanManageShopMembers,
    IsAdminOrClaimOwner,
    IsClaimOwner,
    IsShopManagerOrOwner,
    IsShopMember,
    IsShopOwner,
    IsShopOwnerOrReadOnly,
)
from .serializers import (
    OpeningHoursBulkSerializer,
    OpeningHoursCreateSerializer,
    OpeningHoursSerializer,
    ShopClaimAdminUpdateSerializer,
    ShopClaimCreateSerializer,
    ShopClaimDetailSerializer,
    ShopClaimListSerializer,
    ShopClaimVerifySerializer,
    ShopCreateSerializer,
    ShopDetailSerializer,
    ShopListSerializer,
    ShopMemberCreateSerializer,
    ShopMemberSerializer,
    ShopMemberUpdateSerializer,
    ShopSocialLinkCreateSerializer,
    ShopSocialLinkSerializer,
    ShopTransferOwnershipSerializer,
    ShopUpdateSerializer,
)




# =============================================================================
# Shop Views
# =============================================================================


class ShopViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Shop CRUD operations.
    
    Endpoints:
    - GET /api/shops/ - List all active shops (public)
    - POST /api/shops/ - Create a new shop (authenticated)
    - GET /api/shops/{slug}/ - Retrieve shop details (public)
    - PUT/PATCH /api/shops/{slug}/ - Update shop (owner/manager)
    - DELETE /api/shops/{slug}/ - Delete shop (owner only)
    - GET /api/shops/my-shops/ - List shops owned by current user
    - POST /api/shops/{slug}/transfer-ownership/ - Transfer ownership
    """
    
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "city", "state", "description"]
    ordering_fields = ["name", "city", "created_at"]
    ordering = ["-created_at"]
    filterset_fields = ["city", "state", "country", "is_verified"]
    
    def get_queryset(self):
        """Return appropriate queryset based on action and user."""
        queryset = Shop.objects.select_related("owner").prefetch_related(
            "opening_hours", "social_links", "machines"
        )
        
        # For list views, show only active shops unless admin
        if self.action == "list":
            if not self.request.user.is_staff:
                queryset = queryset.filter(is_active=True)
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return ShopListSerializer
        elif self.action == "create":
            return ShopCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ShopUpdateSerializer
        elif self.action == "transfer_ownership":
            return ShopTransferOwnershipSerializer
        return ShopDetailSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        elif self.action == "create":
            return [permissions.IsAuthenticated()]
        elif self.action in ["update", "partial_update"]:
            return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]
        elif self.action in ["destroy", "transfer_ownership"]:
            return [permissions.IsAuthenticated(), IsShopOwner()]
        return [permissions.IsAuthenticated()]
    
    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_shops(self, request: Request) -> Response:
        """List shops owned by or associated with the current user."""
        owned_shops = Shop.objects.filter(owner=request.user)
        member_shops = Shop.objects.filter(
            members__user=request.user,
            members__is_active=True,
        ).exclude(owner=request.user)
        
        owned_serializer = ShopListSerializer(owned_shops, many=True)
        member_serializer = ShopListSerializer(member_shops, many=True)
        
        return Response({
            "owned": owned_serializer.data,
            "member_of": member_serializer.data,
        })
    
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsShopOwner])
    def transfer_ownership(self, request: Request, slug: str = None) -> Response:
        """Transfer shop ownership to another member."""
        shop = self.get_object()
        
        serializer = ShopTransferOwnershipSerializer(
            data=request.data,
            context={"request": request, "shop": shop}
        )
        serializer.is_valid(raise_exception=True)
        shop = serializer.save()
        
        return Response(
            ShopDetailSerializer(shop).data,
            status=status.HTTP_200_OK
        )
    
    def perform_destroy(self, instance):
        """Soft delete by deactivating."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])


# =============================================================================
# Shop Member Views
# =============================================================================


class ShopMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing shop members/team.
    
    Endpoints:
    - GET /api/shops/{shop_slug}/members/ - List shop members
    - POST /api/shops/{shop_slug}/members/ - Add a member
    - GET /api/shops/{shop_slug}/members/{id}/ - Get member details
    - PUT/PATCH /api/shops/{shop_slug}/members/{id}/ - Update member
    - DELETE /api/shops/{shop_slug}/members/{id}/ - Remove member
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_shop(self) -> Shop:
        """Get the parent shop from URL."""
        if not hasattr(self, "_shop"):
            self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return self._shop
    
    def get_queryset(self):
        """Return members for the specific shop."""
        return ShopMember.objects.filter(
            shop=self.get_shop()
        ).select_related("user").order_by("role", "-created_at")
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return ShopMemberCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ShopMemberUpdateSerializer
        return ShopMemberSerializer
    
    def get_serializer_context(self):
        """Add shop to serializer context."""
        context = super().get_serializer_context()
        context["shop"] = self.get_shop()
        return context
    
    def get_permissions(self):
        """Return permissions based on action."""
        if self.action == "list":
            return [permissions.IsAuthenticated(), IsShopMember()]
        elif self.action == "retrieve":
            return [permissions.IsAuthenticated(), IsShopMember()]
        elif self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), CanManageShopMembers()]
        return super().get_permissions()
    
    def check_object_permissions(self, request, obj):
        """Check permissions against the shop for list actions."""
        if self.action in ["list"]:
            super().check_object_permissions(request, self.get_shop())
        else:
            super().check_object_permissions(request, obj)
    
    def list(self, request, *args, **kwargs):
        """Check shop-level permission before listing."""
        shop = self.get_shop()
        self.check_object_permissions(request, shop)
        return super().list(request, *args, **kwargs)
    
    def perform_destroy(self, instance):
        """Prevent removing the shop owner."""
        if instance.user == instance.shop.owner:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {"detail": "Cannot remove the shop owner. Transfer ownership first."}
            )
        instance.delete()


# =============================================================================
# Opening Hours Views
# =============================================================================


class OpeningHoursViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing shop opening hours.
    
    Endpoints:
    - GET /api/shops/{shop_slug}/hours/ - List opening hours
    - POST /api/shops/{shop_slug}/hours/ - Add opening hour entry
    - PUT /api/shops/{shop_slug}/hours/{id}/ - Update entry
    - DELETE /api/shops/{shop_slug}/hours/{id}/ - Delete entry
    - POST /api/shops/{shop_slug}/hours/bulk/ - Bulk update all hours
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_shop(self) -> Shop:
        """Get the parent shop from URL."""
        if not hasattr(self, "_shop"):
            self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return self._shop
    
    def get_queryset(self):
        """Return hours for the specific shop."""
        return OpeningHours.objects.filter(
            shop=self.get_shop()
        ).order_by("weekday", "from_hour")
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return OpeningHoursCreateSerializer
        elif self.action == "bulk_update":
            return OpeningHoursBulkSerializer
        return OpeningHoursSerializer
    
    def get_serializer_context(self):
        """Add shop to serializer context."""
        context = super().get_serializer_context()
        context["shop"] = self.get_shop()
        return context
    
    def get_permissions(self):
        """Return permissions based on action."""
        if self.action == "list":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]
    
    def list(self, request, *args, **kwargs):
        """Public list of opening hours."""
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=["post"])
    def bulk_update(self, request, shop_slug: str = None) -> Response:
        """Bulk update all opening hours for a shop."""
        shop = self.get_shop()
        
        # Check permissions
        self.check_object_permissions(request, shop)
        
        serializer = OpeningHoursBulkSerializer(
            data=request.data,
            context={"shop": shop}
        )
        serializer.is_valid(raise_exception=True)
        hours = serializer.save()
        
        return Response(
            OpeningHoursSerializer(hours, many=True).data,
            status=status.HTTP_200_OK
        )


# =============================================================================
# Shop Social Link Views
# =============================================================================


class ShopSocialLinkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing shop social links.
    
    Endpoints:
    - GET /api/shops/{shop_slug}/social-links/ - List social links
    - POST /api/shops/{shop_slug}/social-links/ - Add social link
    - PUT/PATCH /api/shops/{shop_slug}/social-links/{id}/ - Update link
    - DELETE /api/shops/{shop_slug}/social-links/{id}/ - Delete link
    """
    
    def get_shop(self) -> Shop:
        """Get the parent shop from URL."""
        if not hasattr(self, "_shop"):
            self._shop = get_object_or_404(Shop, slug=self.kwargs["shop_slug"])
        return self._shop
    
    def get_queryset(self):
        """Return social links for the specific shop."""
        return ShopSocialLink.objects.filter(
            shop=self.get_shop()
        ).order_by("platform")
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return ShopSocialLinkCreateSerializer
        return ShopSocialLinkSerializer
    
    def get_serializer_context(self):
        """Add shop to serializer context."""
        context = super().get_serializer_context()
        context["shop"] = self.get_shop()
        return context
    
    def get_permissions(self):
        """Return permissions based on action."""
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsShopManagerOrOwner()]


# =============================================================================
# Shop Claim Views
# =============================================================================


class ShopClaimViewSet(viewsets.ModelViewSet):
    """
    ViewSet for shop claims.
    
    Endpoints:
    - GET /api/claims/ - List user's claims (or all for admin)
    - POST /api/claims/ - Submit a new claim
    - GET /api/claims/{id}/ - Get claim details
    - DELETE /api/claims/{id}/ - Cancel pending claim
    """
    
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]
    
    def get_queryset(self):
        """Return claims based on user role."""
        if self.request.user.is_staff:
            return ShopClaim.objects.all().select_related("user", "shop")
        return ShopClaim.objects.filter(user=self.request.user).select_related("shop")
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return ShopClaimCreateSerializer
        elif self.action == "retrieve":
            return ShopClaimDetailSerializer
        return ShopClaimListSerializer
    
    def get_permissions(self):
        """Return permissions based on action."""
        if self.action in ["retrieve", "destroy"]:
            return [permissions.IsAuthenticated(), IsAdminOrClaimOwner()]
        return [permissions.IsAuthenticated()]
    
    def perform_destroy(self, instance):
        """Only allow deleting pending claims."""
        if instance.status != ShopClaim.Status.PENDING:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {"detail": "Only pending claims can be cancelled."}
            )
        instance.delete()


class ShopClaimVerifyView(APIView):
    """
    POST /api/claims/verify/
    
    Verify a shop claim using the token from the email.
    Public endpoint (uses token for authentication).
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request: Request) -> Response:
        serializer = ShopClaimVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        
        return Response({
            "message": "Shop claim verified successfully.",
            "shop": ShopListSerializer(claim.shop).data if claim.shop else None,
        })


class ShopClaimAdminUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/claims/{id}/review/
    
    Admin endpoint to approve or reject claims.
    """
    
    queryset = ShopClaim.objects.all()
    serializer_class = ShopClaimAdminUpdateSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def perform_update(self, serializer):
        """Handle claim approval/rejection logic."""
        claim = serializer.save()
        
        # If approved, verify the shop
        if claim.status == ShopClaim.Status.VERIFIED and claim.shop:
            claim.shop.is_verified = True
            claim.shop.owner = claim.user
            claim.shop.save(update_fields=["is_verified", "owner"])


# =============================================================================
# Nearby Shops View
# =============================================================================


class NearbyShopsView(generics.ListAPIView):
    """
    GET /api/shops/nearby/
    
    Find shops near a given location.
    Query params: lat, lng, radius (in km, default 10)
    """
    
    serializer_class = ShopListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Filter shops by distance from coordinates."""
        lat = self.request.query_params.get("lat")
        lng = self.request.query_params.get("lng")
        radius = float(self.request.query_params.get("radius", 10))
        
        if not lat or not lng:
            return Shop.objects.none()
        
        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            return Shop.objects.none()
        
        # Simple bounding box filter (approximate)
        # 1 degree latitude ≈ 111 km
        # 1 degree longitude varies by latitude
        lat_range = radius / 111.0
        lng_range = radius / (111.0 * abs(cos(radians(lat))))
        
        return Shop.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__range=(lat - lat_range, lat + lat_range),
            longitude__range=(lng - lng_range, lng + lng_range),
        )
