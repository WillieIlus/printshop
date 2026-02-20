"""
Email verification service.

Handles OTP code generation, sending verification emails, and code validation.
Uses Django's email backend (console for local, SMTP for production).
"""

from __future__ import annotations

import random
import string
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from accounts.models import EmailVerificationCode, User


def generate_verification_code(length: int = 6) -> str:
    """Generate a random numeric verification code."""
    return "".join(random.choices(string.digits, k=length))


def create_verification_code(user: User, expiry_minutes: int = 10) -> EmailVerificationCode:
    """
    Create a new verification code for the user.
    Old codes remain in DB but only the latest active one is used.
    """
    code = generate_verification_code()
    expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
    return EmailVerificationCode.objects.create(
        user=user,
        code=code,
        expires_at=expires_at,
    )


def send_verification_code(user: User) -> EmailVerificationCode:
    """
    Create a new verification code and send it via email.

    Uses Django's email backend (settings.EMAIL_BACKEND).
    For local dev: console backend prints to stdout.
    For production: configure SMTP in settings.

    Returns:
        The created EmailVerificationCode instance.
    """
    verification_code = create_verification_code(user)

    subject = "Your verification code"
    message = f"""
Hello {user.first_name or 'there'},

Your verification code is: {verification_code.code}

This code expires in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
The Team
    """.strip()

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return verification_code
