# accounts/urls.py

"""
URL configuration for the accounts app.

Includes authentication endpoints and CRUD routes for users, profiles, and social links.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    EmailConfirmationView,
    GitHubLoginView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfileSocialLinksView,
    ProfileViewSet,
    RegisterView,
    SocialLinkViewSet,
    UserViewSet,
)

app_name = "accounts"

# Router for ViewSets
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"profiles", ProfileViewSet, basename="profile")
router.register(r"social-links", SocialLinkViewSet, basename="sociallink")

# Authentication URLs
auth_urlpatterns = [
    # Registration & confirmation
    path("register/", RegisterView.as_view(), name="register"),
    path("confirm-email/", EmailConfirmationView.as_view(), name="confirm-email"),
    
    # Login/Logout
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    
    # Password management
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    
    # Social authentication
    path("social/google/", GoogleLoginView.as_view(), name="social-google"),
    path("social/github/", GitHubLoginView.as_view(), name="social-github"),
]

urlpatterns = [
    # Auth endpoints under /api/auth/
    path("auth/", include((auth_urlpatterns, "auth"))),
    
    # CRUD endpoints
    path("", include(router.urls)),
    
    # Nested profile social links (read-only)
    path(
        "profiles/<int:profile_id>/social-links/",
        ProfileSocialLinksView.as_view(),
        name="profile-social-links",
    ),
]