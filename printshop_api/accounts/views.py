# accounts/views.py

"""
Django REST Framework views for authentication and user management.

Implements:
- Registration and email confirmation
- JWT-based login/logout
- Password change and reset flows
- Social authentication (Google, GitHub)
- User, Profile, and SocialLink CRUD
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Profile, SocialLink
from .permissions import IsAdminOrSelf, IsOwnerOrReadOnly, IsProfileOwner
from .serializers import (
    CustomTokenObtainPairSerializer,
    EmailConfirmationSerializer,
    GitHubLoginSerializer,
    GoogleLoginSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    SocialLinkCreateSerializer,
    SocialLinkSerializer,
    SocialLoginResponseSerializer,
    UserDetailSerializer,
    UserSerializer,
)

User = get_user_model()


# =============================================================================
# Registration & Email Confirmation Views
# =============================================================================


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    
    Register a new user. Creates an inactive user and sends
    a confirmation email with activation link.
    """
    
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        response_data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "message": "Registration successful. Please check your email to confirm your account.",
        }
        
        return Response(
            RegisterResponseSerializer(response_data).data,
            status=status.HTTP_201_CREATED,
        )


class EmailConfirmationView(APIView):
    """
    POST /api/auth/confirm-email/
    
    Confirm user's email address and activate the account.
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request: Request) -> Response:
        serializer = EmailConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {"message": "Email confirmed successfully. You can now log in."},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# Login & Logout Views
# =============================================================================


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    
    Authenticate user with email and password.
    Returns JWT access and refresh tokens.
    """
    
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    
    Logout user by blacklisting the refresh token.
    Requires authentication.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {"message": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# Password Management Views
# =============================================================================


class PasswordChangeView(APIView):
    """
    POST /api/auth/password/change/
    
    Change password for authenticated user.
    Requires current password verification.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password/reset/
    
    Request a password reset email.
    Does not reveal whether the email exists (security).
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Always return success to not reveal if email exists
        return Response(
            {"message": "If an account with this email exists, a password reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password/reset/confirm/
    
    Set new password using reset token from email.
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# Social Authentication Views
# =============================================================================


class GoogleLoginView(APIView):
    """
    POST /api/auth/social/google/
    
    Authenticate with Google OAuth.
    Accepts access token from frontend, validates with Google,
    creates/retrieves user, and returns JWT tokens.
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request: Request) -> Response:
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return Response(
            SocialLoginResponseSerializer(result).data,
            status=status.HTTP_200_OK,
        )


class GitHubLoginView(APIView):
    """
    POST /api/auth/social/github/
    
    Authenticate with GitHub OAuth.
    Accepts access token from frontend, validates with GitHub,
    creates/retrieves user, and returns JWT tokens.
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request: Request) -> Response:
        serializer = GitHubLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return Response(
            SocialLoginResponseSerializer(result).data,
            status=status.HTTP_200_OK,
        )


# =============================================================================
# User Views
# =============================================================================


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model.
    
    Endpoints:
    - GET /api/users/ - List all users (admin only)
    - GET /api/users/{id}/ - Retrieve user (admin or self)
    - GET /api/users/me/ - Retrieve current user
    - PATCH /api/users/me/ - Update current user
    """
    
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve actions."""
        if self.action in ["retrieve", "me"]:
            return UserDetailSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action == "list":
            return [permissions.IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=["get", "patch"], permission_classes=[permissions.IsAuthenticated])
    def me(self, request: Request) -> Response:
        """Get or update the current authenticated user."""
        user = request.user
        
        if request.method == "PATCH":
            serializer = UserSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(UserDetailSerializer(user).data)
        
        return Response(UserDetailSerializer(user).data)


# =============================================================================
# Profile Views
# =============================================================================


class ProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Profile model.
    
    Endpoints:
    - GET /api/profiles/{id}/ - Retrieve profile (any authenticated user)
    - PUT/PATCH /api/profiles/{id}/ - Update profile (owner only)
    - GET /api/profiles/me/ - Retrieve current user's profile
    - PATCH /api/profiles/me/ - Update current user's profile
    """
    
    queryset = Profile.objects.select_related("user").prefetch_related("social_links")
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    http_method_names = ["get", "put", "patch", "head", "options"]
    
    def get_serializer_class(self):
        """Use update serializer for write operations."""
        if self.action in ["update", "partial_update"]:
            return ProfileUpdateSerializer
        return ProfileSerializer
    
    @action(detail=False, methods=["get", "patch"], permission_classes=[permissions.IsAuthenticated])
    def me(self, request: Request) -> Response:
        """Get or update the current authenticated user's profile."""
        profile = Profile.objects.select_related("user").prefetch_related(
            "social_links"
        ).get(user=request.user)
        
        if request.method == "PATCH":
            serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        
        return Response(ProfileSerializer(profile).data)


# =============================================================================
# SocialLink Views
# =============================================================================


class SocialLinkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SocialLink model.
    
    Operates on the current user's profile social links.
    
    Endpoints:
    - GET /api/social-links/ - List current user's social links
    - POST /api/social-links/ - Create a social link
    - GET /api/social-links/{id}/ - Retrieve a social link
    - PUT/PATCH /api/social-links/{id}/ - Update a social link
    - DELETE /api/social-links/{id}/ - Delete a social link
    """
    
    permission_classes = [permissions.IsAuthenticated, IsProfileOwner]
    
    def get_queryset(self):
        """Return social links for the current user's profile only."""
        return SocialLink.objects.filter(
            profile__user=self.request.user
        ).order_by("platform")
    
    def get_serializer_class(self):
        """Use create serializer for POST."""
        if self.action == "create":
            return SocialLinkCreateSerializer
        return SocialLinkSerializer
    
    def get_serializer_context(self):
        """Add profile to context for validation and creation."""
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context["profile"] = getattr(self.request.user, "profile", None)
        return context


class ProfileSocialLinksView(generics.ListAPIView):
    """
    GET /api/profiles/{profile_id}/social-links/
    
    List social links for a specific profile (read-only, any authenticated user).
    """
    
    serializer_class = SocialLinkSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return social links for the specified profile."""
        profile_id = self.kwargs.get("profile_id")
        return SocialLink.objects.filter(profile_id=profile_id).order_by("platform")