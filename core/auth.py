"""
Core Auth Module - Backward Compatibility Layer
Re-exports auth functions from apps.users.services
"""
import secrets
from datetime import timedelta
from django.utils import timezone

# Keep original functions for backward compatibility
from apps.users.models import PseudonymousUser, hash_email
from apps.users.services import (
    UserRegistrationService,
    UserAuthenticationService,
)


def generate_magic_token():
    """Generate a secure magic token"""
    return secrets.token_urlsafe(32)


def register_pseudonymous_user(alias, email, password):
    """
    Register a new pseudonymous user with required fields.
    Returns (user, error_message) tuple.
    """
    service = UserRegistrationService()
    result = service.register(alias, email, password)
    
    if result.success:
        return result.user, None
    return None, result.error


def authenticate_pseudonymous_user(alias, password):
    """Check alias + password for existing users"""
    service = UserAuthenticationService()
    result = service.authenticate_with_password(alias, password)
    
    if result.success:
        return result.user
    return None


def get_or_create_pseudonymous_user(alias, email=None, password=None):
    """
    DEPRECATED: Use register_pseudonymous_user for new registrations
    and authenticate_pseudonymous_user for logins.
    """
    user, created = PseudonymousUser.objects.get_or_create(
        alias=alias,
        defaults={'email': email or None}
    )

    if created and password:
        user.set_password(password)
        if email:
            user.set_email(email)

    return user, created


def send_magic_link(user, request):
    """Send or display magic link for a verified user"""
    service = UserAuthenticationService()
    return service.generate_magic_link(user, request)


def verify_magic_token(token):
    """Verify magic token and return user if valid"""
    service = UserAuthenticationService()
    return service.verify_magic_token(token)
