# accounts/permissions.py

"""
Custom permission classes for the accounts app.
"""

from __future__ import annotations

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAdminOrSelf(permissions.BasePermission):
    """
    Allow access if user is admin or is accessing their own resource.
    """
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        # Admin users have full access
        if request.user.is_staff:
            return True
        
        # Users can access their own record
        return obj == request.user or getattr(obj, "user", None) == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access to any authenticated user.
    Write access only to the owner.
    """
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        # Read permissions for any authenticated request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only to owner
        if hasattr(obj, "user"):
            return obj.user == request.user
        
        return obj == request.user


class IsProfileOwner(permissions.BasePermission):
    """
    Allow access only to social links belonging to the user's profile.
    """
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        # Check if the social link belongs to the requesting user's profile
        return obj.profile.user == request.user