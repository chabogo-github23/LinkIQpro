"""
Users Domain Services
Business logic for user operations following SOLID principles
"""
from typing import Optional, Tuple
from dataclasses import dataclass
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from .models import PseudonymousUser, AuthToken
from .repositories import UserRepository, AuthTokenRepository


@dataclass
class RegistrationResult:
    success: bool
    user: Optional[PseudonymousUser] = None
    error: Optional[str] = None


@dataclass  
class AuthenticationResult:
    success: bool
    user: Optional[PseudonymousUser] = None
    magic_link: Optional[str] = None
    error: Optional[str] = None


class UserRegistrationService:
    """
    Service for user registration
    Single Responsibility: Handle new user registration
    """
    
    def __init__(self, user_repo: UserRepository = None):
        self.user_repo = user_repo or UserRepository()
    
    def register(self, alias: str, email: str, password: str) -> RegistrationResult:
        """Register a new user with validation"""
        
        # Validate alias
        if not alias or len(alias) < 3:
            return RegistrationResult(success=False, error='Alias must be at least 3 characters long.')
        
        if self.user_repo.alias_exists(alias):
            return RegistrationResult(success=False, error=f'User with alias "{alias}" already exists.')
        
        # Validate email
        if not email or '@' not in email:
            return RegistrationResult(success=False, error='Please enter a valid email address.')
        
        if self.user_repo.email_exists(email):
            return RegistrationResult(success=False, error='A user with this email already exists.')
        
        # Validate password
        if not password or len(password) < 6:
            return RegistrationResult(success=False, error='Password must be at least 6 characters long.')
        
        # Create user
        user = self.user_repo.create_user(
            alias=alias,
            email=email,
            password=password
        )
        
        return RegistrationResult(success=True, user=user)


class UserAuthenticationService:
    """
    Service for user authentication
    Single Responsibility: Handle user authentication flows
    """
    
    def __init__(self, user_repo: UserRepository = None, token_repo: AuthTokenRepository = None):
        self.user_repo = user_repo or UserRepository()
        self.token_repo = token_repo or AuthTokenRepository()
    
    def authenticate_with_password(self, alias: str, password: str) -> AuthenticationResult:
        """Authenticate user with alias and password"""
        user = self.user_repo.get_by_alias(alias)
        
        if not user:
            return AuthenticationResult(success=False, error='No account found. Please register first.')
        
        if not user.check_password(password):
            return AuthenticationResult(success=False, error='Incorrect password. Try again.')
        
        return AuthenticationResult(success=True, user=user)
    
    def generate_magic_link(self, user: PseudonymousUser, request) -> str:
        """Generate a magic link for the user"""
        import secrets
        
        token = secrets.token_urlsafe(32)
        user.magic_token = token
        user.magic_token_expires = timezone.now() + timezone.timedelta(hours=24)
        user.save()
        
        magic_link = request.build_absolute_uri(
            reverse('core:verify_magic_link') + f'?token={token}'
        )
        
        return magic_link
    
    def verify_magic_token(self, token: str) -> Optional[PseudonymousUser]:
        """Verify a magic link token and return the user"""
        user = self.user_repo.get_by_magic_token(token)
        
        if user:
            # Invalidate token after verification
            user.magic_token = None
            user.magic_token_expires = None
            user.save()
        
        return user
    
    def login_user(self, request, user: PseudonymousUser) -> None:
        """Set up user session"""
        request.session['pseudonymous_user_id'] = str(user.id)
        request.session.set_expiry(86400)  # 24 hours
        request.session.save()
        
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
    
    def logout_user(self, request) -> Optional[PseudonymousUser]:
        """Clear user session and return the logged out user"""
        user_id = request.session.pop('pseudonymous_user_id', None)
        if user_id:
            return self.user_repo.get_by_id(user_id)
        return None


class PasswordResetService:
    """
    Service for password reset functionality
    Single Responsibility: Handle password reset flows
    """
    
    def __init__(self, user_repo: UserRepository = None, token_repo: AuthTokenRepository = None):
        self.user_repo = user_repo or UserRepository()
        self.token_repo = token_repo or AuthTokenRepository()
    
    def request_reset(self, email: str, request) -> Tuple[bool, str]:
        """Request a password reset for the given email"""
        user = self.user_repo.get_by_email(email)
        
        if not user:
            return False, "No account found with this email."
        
        # Generate token
        auth_token = self.token_repo.create_token(user, hours_valid=1)
        
        # Build reset URL
        reset_url = request.build_absolute_uri(
            reverse('core:password_reset_confirm', args=[auth_token.token])
        )
        
        # Send email
        email_body = f"""
        Hi {user.alias},

        Someone requested to reset your ShadowIQ account password.
        If this was you, click the link below:

        {reset_url}

        This link expires in 1 hour.
        If you did not request this, ignore this email.
        """
        
        try:
            send_mail(
                subject="Password Reset - ShadowIQ",
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return True, "Password reset link has been sent to your email."
        except Exception as e:
            return False, f"Failed to send email: {e}"
    
    def confirm_reset(self, token: str, new_password: str) -> Tuple[bool, str]:
        """Confirm password reset with token"""
        auth_token = self.token_repo.get_valid_token(token)
        
        if not auth_token:
            return False, "Invalid or expired link."
        
        if not new_password:
            return False, "Password required."
        
        # Reset password
        auth_token.user.set_password(new_password)
        self.token_repo.invalidate_token(auth_token)
        
        return True, "Your password has been reset."


class UserManagementService:
    """
    Service for admin user management
    Single Responsibility: Admin operations on users
    """
    
    def __init__(self, user_repo: UserRepository = None):
        self.user_repo = user_repo or UserRepository()
    
    def create_user(self, alias: str, email: str, password: str, role: str) -> Tuple[Optional[PseudonymousUser], Optional[str]]:
        """Admin creates a new user"""
        # Validation
        if not alias or len(alias) < 3:
            return None, 'Alias must be at least 3 characters long.'
        
        if self.user_repo.alias_exists(alias):
            return None, f'User with alias "{alias}" already exists.'
        
        if not email or '@' not in email:
            return None, 'Please enter a valid email address.'
        
        if self.user_repo.email_exists(email):
            return None, 'A user with this email already exists.'
        
        if not password or len(password) < 6:
            return None, 'Password must be at least 6 characters long.'
        
        user = self.user_repo.create_user(
            alias=alias,
            email=email,
            password=password,
            is_admin=(role == 'admin'),
            is_analyst=(role == 'analyst')
        )
        
        return user, None
    
    def update_user(self, user: PseudonymousUser, alias: str, role: str, 
                   is_active: bool, new_password: str = None) -> Tuple[bool, Optional[str]]:
        """Admin updates an existing user"""
        if not alias or len(alias) < 3:
            return False, 'Alias must be at least 3 characters long.'
        
        if alias != user.alias and self.user_repo.alias_exists(alias):
            return False, f'User with alias "{alias}" already exists.'
        
        if new_password and len(new_password) < 6:
            return False, 'New password must be at least 6 characters long.'
        
        self.user_repo.update_user(
            user,
            alias=alias,
            is_admin=(role == 'admin'),
            is_analyst=(role == 'analyst'),
            is_active=is_active
        )
        
        if new_password:
            user.set_password(new_password)
        
        return True, None
    
    def delete_user(self, user: PseudonymousUser, requesting_user: PseudonymousUser) -> Tuple[bool, Optional[str]]:
        """Admin deletes a user"""
        if user.id == requesting_user.id:
            return False, 'You cannot delete your own account.'
        
        self.user_repo.delete_user(user)
        return True, None
    
    def get_user_stats(self) -> dict:
        """Get user statistics"""
        return self.user_repo.get_user_counts()
