# accounts/tests.py

"""
Tests for user, profile, and social links update flows.

Critical flows for production:
- PATCH /api/users/me/ - Update user (first_name, last_name)
- PATCH /api/profiles/me/ - Update profile (bio, avatar, etc)
- Social links CRUD via /api/social-links/
- Auth: login, register, token refresh
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Profile, SocialLink

User = get_user_model()


@pytest.fixture
def user_with_profile(db):
    """Create a user with profile (required for profile/social endpoints)."""
    user = User.objects.create_user(
        email="testuser@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )
    Profile.objects.create(user=user)
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, user_with_profile):
    api_client.force_authenticate(user=user_with_profile)
    return api_client


# =============================================================================
# User Update (PATCH /api/users/me/)
# =============================================================================


class TestUserMeEndpoint:
    """Test PATCH /api/users/me/ for profile updates."""

    def test_get_me_authenticated(self, auth_client, user_with_profile):
        """GET /api/users/me/ returns current user."""
        response = auth_client.get("/api/users/me/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == user_with_profile.email
        assert data["first_name"] == "Test"
        assert data["last_name"] == "User"
        assert "profile_id" in data

    def test_get_me_unauthenticated(self, api_client):
        """GET /api/users/me/ requires auth."""
        response = api_client.get("/api/users/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_me_authenticated(self, auth_client, user_with_profile):
        """PATCH /api/users/me/ updates first_name and last_name."""
        response = auth_client.patch(
            "/api/users/me/",
            {"first_name": "Updated", "last_name": "Name"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"

        user_with_profile.refresh_from_db()
        assert user_with_profile.first_name == "Updated"
        assert user_with_profile.last_name == "Name"

    def test_patch_me_partial(self, auth_client):
        """PATCH /api/users/me/ accepts partial updates."""
        response = auth_client.patch(
            "/api/users/me/",
            {"first_name": "OnlyFirst"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["first_name"] == "OnlyFirst"


# =============================================================================
# Profile Update (PATCH /api/profiles/me/)
# =============================================================================


class TestProfileMeEndpoint:
    """Test PATCH /api/profiles/me/ for profile updates."""

    def test_get_profile_me(self, auth_client, user_with_profile):
        """GET /api/profiles/me/ returns current user's profile."""
        response = auth_client.get("/api/profiles/me/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_email"] == user_with_profile.email
        assert "social_links" in data

    def test_patch_profile_me(self, auth_client, user_with_profile):
        """PATCH /api/profiles/me/ updates profile fields."""
        response = auth_client.patch(
            "/api/profiles/me/",
            {"bio": "My bio", "website": "https://example.com", "location": "Nairobi"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["bio"] == "My bio"
        assert data["website"] == "https://example.com"
        assert data["location"] == "Nairobi"

        profile = user_with_profile.profile
        profile.refresh_from_db()
        assert profile.bio == "My bio"
        assert profile.website == "https://example.com"


# =============================================================================
# Social Links CRUD
# =============================================================================


class TestSocialLinksCRUD:
    """Test social links create, read, update, delete."""

    def test_create_social_link(self, auth_client, user_with_profile):
        """POST /api/social-links/ creates a social link."""
        response = auth_client.post(
            "/api/social-links/",
            {
                "platform": "twitter",
                "url": "https://twitter.com/testuser",
                "username": "testuser",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["platform"] == "twitter"
        assert data["url"] == "https://twitter.com/testuser"
        assert data["username"] == "testuser"

        assert SocialLink.objects.filter(profile=user_with_profile.profile).count() == 1

    def test_list_social_links(self, auth_client, user_with_profile):
        """GET /api/social-links/ lists current user's links."""
        SocialLink.objects.create(
            profile=user_with_profile.profile,
            platform="github",
            url="https://github.com/test",
        )
        response = auth_client.get("/api/social-links/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Paginated response has 'results' key
        results = data["results"] if "results" in data else data
        assert len(results) == 1
        assert results[0]["platform"] == "github"

    def test_update_social_link(self, auth_client, user_with_profile):
        """PATCH /api/social-links/{id}/ updates a link."""
        link = SocialLink.objects.create(
            profile=user_with_profile.profile,
            platform="linkedin",
            url="https://linkedin.com/in/old",
        )
        response = auth_client.patch(
            f"/api/social-links/{link.id}/",
            {"url": "https://linkedin.com/in/new"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        link.refresh_from_db()
        assert link.url == "https://linkedin.com/in/new"

    def test_delete_social_link(self, auth_client, user_with_profile):
        """DELETE /api/social-links/{id}/ removes a link."""
        link = SocialLink.objects.create(
            profile=user_with_profile.profile,
            platform="instagram",
            url="https://instagram.com/test",
        )
        response = auth_client.delete(f"/api/social-links/{link.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not SocialLink.objects.filter(profile=user_with_profile.profile).exists()


# =============================================================================
# Auth Endpoints
# =============================================================================


@pytest.mark.django_db
class TestAuthEndpoints:
    """Test login, register, token refresh."""

    def test_login(self, api_client, user_with_profile):
        """POST /api/auth/login/ returns JWT tokens."""
        response = api_client.post(
            "/api/auth/login/",
            {"email": "testuser@example.com", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access" in data
        assert "refresh" in data

    def test_login_legacy_path(self, api_client, user_with_profile):
        """POST /api/auth/api-auth/login/ (legacy) still works."""
        response = api_client.post(
            "/api/auth/api-auth/login/",
            {"email": "testuser@example.com", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.json()

    def test_register(self, api_client):
        """POST /api/auth/register/ creates a user."""
        response = api_client.post(
            "/api/auth/register/",
            {
                "email": "newuser@example.com",
                "password": "securepass123",
                "password_confirmation": "securepass123",
                "first_name": "New",
                "last_name": "User",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert User.objects.filter(email="newuser@example.com").exists()
        assert Profile.objects.filter(user__email="newuser@example.com").exists()

    def test_token_refresh(self, api_client, user_with_profile):
        """POST /api/auth/token/refresh/ refreshes access token."""
        login_resp = api_client.post(
            "/api/auth/login/",
            {"email": "testuser@example.com", "password": "testpass123"},
            format="json",
        )
        refresh = login_resp.json()["refresh"]

        response = api_client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.json()
