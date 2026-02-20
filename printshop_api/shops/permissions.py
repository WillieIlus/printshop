# shops/permissions.py

"""
Custom permission classes for the shops app.

Handles shop ownership, membership roles, and claim verification.
"""

from __future__ import annotations

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import Shop, ShopMember


class IsShopOwner(permissions.BasePermission):
    """
    Allow access only to the shop owner.
    For list/create: checks shop_slug in URL. For retrieve/update/delete: checks object's shop.
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check shop ownership when shop_slug is in URL (list/create)."""
        shop_slug = view.kwargs.get("shop_slug")
        if not shop_slug:
            return True
        try:
            shop = Shop.objects.get(slug=shop_slug)
            return shop.owner == request.user
        except Shop.DoesNotExist:
            return False
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        # Handle Shop object directly
        if isinstance(obj, Shop):
            return obj.owner == request.user
        
        # Handle objects with a shop FK (ShopMember, OpeningHours, ShopSocialLink)
        if hasattr(obj, "shop"):
            return obj.shop.owner == request.user
        
        return False


class IsShopOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access to anyone, write access to shop owner only.
    """
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if isinstance(obj, Shop):
            return obj.owner == request.user
        
        if hasattr(obj, "shop"):
            return obj.shop.owner == request.user
        
        return False


class IsShopMember(permissions.BasePermission):
    """
    Allow access to any active member of the shop.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """For list/create: check shop access via shop_slug in URL."""
        shop_slug = view.kwargs.get("shop_slug")
        if not shop_slug:
            return True
        try:
            shop = Shop.objects.get(slug=shop_slug)
        except Shop.DoesNotExist:
            return False
        if shop.owner == request.user:
            return True
        return ShopMember.objects.filter(
            shop=shop, user=request.user, is_active=True
        ).exists()

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        shop = obj if isinstance(obj, Shop) else getattr(obj, "shop", None)
        
        if not shop:
            return False
        
        # Owner always has access
        if shop.owner == request.user:
            return True
        
        # Check for active membership
        return ShopMember.objects.filter(
            shop=shop,
            user=request.user,
            is_active=True,
        ).exists()


class IsShopManagerOrOwner(permissions.BasePermission):
    """
    Allow access to shop owners or users with MANAGER/OWNER role.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """For list/create: check shop manager/owner access via shop_slug in URL."""
        shop_slug = view.kwargs.get("shop_slug")
        if not shop_slug:
            return True
        try:
            shop = Shop.objects.get(slug=shop_slug)
        except Shop.DoesNotExist:
            return False
        if shop.owner == request.user:
            return True
        return ShopMember.objects.filter(
            shop=shop,
            user=request.user,
            role__in=[ShopMember.Role.OWNER, ShopMember.Role.MANAGER],
            is_active=True,
        ).exists()

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        shop = obj if isinstance(obj, Shop) else getattr(obj, "shop", None)
        
        if not shop:
            return False
        
        # Shop owner always has access
        if shop.owner == request.user:
            return True
        
        # Check for manager/owner role
        return ShopMember.objects.filter(
            shop=shop,
            user=request.user,
            role__in=[ShopMember.Role.OWNER, ShopMember.Role.MANAGER],
            is_active=True,
        ).exists()


class CanManageShopMembers(permissions.BasePermission):
    """
    Allow shop owners and managers to manage team members.
    Managers cannot add/remove other managers or owners.
    """
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.user.is_authenticated
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        # Get the shop from the member object
        shop = obj.shop if hasattr(obj, "shop") else None
        
        if not shop:
            return False
        
        # Owner can manage anyone
        if shop.owner == request.user:
            return True
        
        # Get the requester's membership
        try:
            requester_membership = ShopMember.objects.get(
                shop=shop,
                user=request.user,
                is_active=True,
            )
        except ShopMember.DoesNotExist:
            return False
        
        # Managers can only manage staff and designers, not other managers/owners
        if requester_membership.role == ShopMember.Role.MANAGER:
            if obj.role in [ShopMember.Role.OWNER, ShopMember.Role.MANAGER]:
                return False
            return True
        
        return False


class IsClaimOwner(permissions.BasePermission):
    """
    Allow access only to the user who submitted the claim.
    """
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        return obj.user == request.user


class IsAdminOrClaimOwner(permissions.BasePermission):
    """
    Allow access to admins or the claim owner.
    """
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if request.user.is_staff:
            return True
        return obj.user == request.user