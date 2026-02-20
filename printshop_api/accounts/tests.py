"""
Tests for accounts app: signup, email verification, login, role switching.
"""

from datetime import timedelta

import pytest
from django.core import mail
from django.test import override_settings
from django.contrib.auth import get_user_model
from rest_framework import status

from accounts.models import EmailVerificationCode, Profile

User = get_user_model()


@pytest.fixture
def verified_user(db):
    """Create a verified user for login tests."""
    return User.objects.create_user(
        email="verified@example.com",
        password="testpass123",
        first_name="Verified",
        last_name="User",
        email_verified=True,
    )


@pytest.fixture
def unverified_user(db):
    """Create an unverified user."""
    user = User.objects.create_user(
        email="unverified@example.com",
        password="testpass123",
        first_name="Unverified",
        last_name="User",
        email_verified=False,
    )
    Profile.objects.get_or_create(user=user)
    return user


# =============================================================================
# Signup Tests
# =============================================================================


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_signup_creates_user_and_sends_verification_code(api_client, db):
    """Signup creates user, sends verification code email, returns expected payload."""
    response = api_client.post(
        "/api/auth/signup/",
        {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "password_confirmation": "SecurePass123!",
            "first_name": "New",
            "last_name": "User",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["email"] == "newuser@example.com"
    assert response.data["message"] == "verification_sent"

    user = User.objects.get(email="newuser@example.com")
    assert user.email_verified is False
    assert user.role == User.Role.CUSTOMER

    # Code was created
    code = EmailVerificationCode.objects.filter(user=user).order_by("-created_at").first()
    assert code is not None
    assert len(code.code) == 6
    assert code.used_at is None

    # Email was sent
    assert len(mail.outbox) == 1
    assert code.code in mail.outbox[0].body
    assert "newuser@example.com" in mail.outbox[0].to


def test_signup_duplicate_email_returns_400(api_client, user):
    """Signup with existing email returns validation error."""
    response = api_client.post(
        "/api/auth/signup/",
        {
            "email": user.email,
            "password": "SecurePass123!",
            "password_confirmation": "SecurePass123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Verify Tests
# =============================================================================


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_verify_with_correct_code_sets_email_verified(api_client, db):
    """Verify with correct code marks user as verified."""
    user = User.objects.create_user(
        email="verify@example.com",
        password="testpass123",
        email_verified=False,
    )
    Profile.objects.get_or_create(user=user)
    code_obj = EmailVerificationCode.objects.create(
        user=user,
        code="123456",
        expires_at=user.created_at + timedelta(minutes=10),
    )

    response = api_client.post(
        "/api/auth/email/verify/",
        {"email": "verify@example.com", "code": "123456"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["message"] == "verified"

    user.refresh_from_db()
    assert user.email_verified is True

    code_obj.refresh_from_db()
    assert code_obj.used_at is not None


def test_verify_with_wrong_code_returns_400(api_client, unverified_user):
    """Verify with wrong code returns validation error and increments attempts."""
    EmailVerificationCode.objects.create(
        user=unverified_user,
        code="123456",
        expires_at=unverified_user.created_at + timedelta(minutes=10),
    )

    response = api_client.post(
        "/api/auth/email/verify/",
        {"email": unverified_user.email, "code": "999999"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    code = EmailVerificationCode.objects.get(user=unverified_user)
    assert code.attempts == 1
    unverified_user.refresh_from_db()
    assert unverified_user.email_verified is False


# =============================================================================
# Login Tests
# =============================================================================


def test_login_before_verification_returns_403(api_client, unverified_user):
    """Login before email verification returns 403 with expected payload."""
    response = api_client.post(
        "/api/auth/login/",
        {"email": unverified_user.email, "password": "testpass123"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["detail"] == "Email not verified"
    assert response.data["code"] == "email_not_verified"


def test_login_after_verification_returns_tokens(api_client, verified_user):
    """Login after verification returns JWT tokens."""
    Profile.objects.get_or_create(user=verified_user)
    response = api_client.post(
        "/api/auth/login/",
        {"email": verified_user.email, "password": "testpass123"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


# =============================================================================
# Resend Tests
# =============================================================================


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_resend_generates_new_code(api_client, unverified_user):
    """Resend generates new code and sends email."""
    old_code = EmailVerificationCode.objects.create(
        user=unverified_user,
        code="111111",
        expires_at=unverified_user.created_at + timedelta(minutes=10),
    )

    mail.outbox.clear()
    response = api_client.post(
        "/api/auth/email/resend/",
        {"email": unverified_user.email},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["message"] == "resent"

    # New code exists (latest is checked for verification)
    new_codes = EmailVerificationCode.objects.filter(user=unverified_user).order_by("-created_at")
    assert new_codes.count() >= 2
    latest = new_codes.first()
    assert latest.code != old_code.code

    assert len(mail.outbox) == 1
    assert latest.code in mail.outbox[0].body


def test_resend_for_nonexistent_email_returns_success(api_client, db):
    """Resend for nonexistent email still returns 200 (don't reveal)."""
    response = api_client.post(
        "/api/auth/email/resend/",
        {"email": "nonexistent@example.com"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["message"] == "resent"


def test_resend_rate_limit(api_client, db):
    """Resend rate limited to 3 per minute per email."""
    # Use unique email to avoid cache pollution from other tests
    user = User.objects.create_user(
        email="ratelimit@example.com",
        password="testpass123",
        email_verified=False,
    )
    Profile.objects.get_or_create(user=user)

    for _ in range(3):
        response = api_client.post(
            "/api/auth/email/resend/",
            {"email": "ratelimit@example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    response = api_client.post(
        "/api/auth/email/resend/",
        {"email": "ratelimit@example.com"},
        format="json",
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.data["code"] == "rate_limited"


# =============================================================================
# Role Update Tests
# =============================================================================


def test_patch_me_updates_role_to_printer(api_client, verified_user):
    """PATCH /api/users/me/ can update role to PRINTER."""
    Profile.objects.get_or_create(user=verified_user)
    api_client.force_authenticate(user=verified_user)

    response = api_client.patch(
        "/api/users/me/",
        {"role": "PRINTER"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == "PRINTER"

    verified_user.refresh_from_db()
    assert verified_user.role == User.Role.PRINTER


def test_patch_me_updates_role_back_to_customer(api_client, verified_user):
    """PATCH /api/users/me/ can update role from PRINTER to CUSTOMER."""
    verified_user.role = User.Role.PRINTER
    verified_user.save()
    Profile.objects.get_or_create(user=verified_user)
    api_client.force_authenticate(user=verified_user)

    response = api_client.patch(
        "/api/users/me/",
        {"role": "CUSTOMER"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == "CUSTOMER"


def test_patch_me_invalid_role_returns_400(api_client, verified_user):
    """PATCH /api/users/me/ with invalid role returns 400."""
    api_client.force_authenticate(user=verified_user)

    response = api_client.patch(
        "/api/users/me/",
        {"role": "INVALID"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
