"""
Users Domain Models
- PseudonymousUser: Core user model with privacy-first design
- AuthToken: Magic link and session tokens
"""
import hashlib
import uuid
import secrets
import string
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


def hash_email(email):
    """Hash an email address using SHA-256 for secure storage"""
    if not email:
        return None
    normalized_email = email.strip().lower()
    return hashlib.sha256(normalized_email.encode('utf-8')).hexdigest()


def check_email_hash(raw_email, hashed_email):
    """Check if a raw email matches the stored hash"""
    if not raw_email or not hashed_email:
        return False
    return hash_email(raw_email) == hashed_email


class PseudonymousUser(models.Model):
    """
    Privacy-first user model with pseudonymous identity.
    Supports both magic link and password authentication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alias = models.CharField(max_length=255, unique=True)
    email = models.EmailField(null=True, blank=True)  # Deprecated - kept for migration
    email_hash = models.CharField(max_length=64, null=True, blank=True, unique=True)
    password_hash = models.CharField(max_length=255, null=True, blank=True)
    magic_token = models.CharField(max_length=255, unique=True, null=True, blank=True)
    magic_token_expires = models.DateTimeField(null=True, blank=True)
    
    # Role flags
    is_admin = models.BooleanField(default=False)
    is_sub_admin = models.BooleanField(default=False)
    is_analyst = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(default=timezone.now)
    parent_admin = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_users'
    )

    class Meta:
        ordering = ['-created_at']
        db_table = 'core_pseudonymoususer'  # Keep existing table name

    def __str__(self):
        return self.alias

    def get_username(self):
        return self.alias

    def set_password(self, raw_password):
        """Hashes and sets a user's password"""
        self.password_hash = make_password(raw_password)
        self.save(update_fields=['password_hash'])

    def check_password(self, raw_password):
        if not self.password_hash:
            return False
        return check_password(raw_password, self.password_hash)

    def set_email(self, raw_email):
        """Hash and store the email address"""
        if raw_email:
            self.email_hash = hash_email(raw_email)
            self.email = None  # Clear plaintext email for security
            self.save(update_fields=['email_hash', 'email'])

    def check_email(self, raw_email):
        """Check if the provided email matches the stored hash"""
        return check_email_hash(raw_email, self.email_hash)

    @classmethod
    def get_by_email(cls, raw_email):
        """Find a user by their email (hashed lookup)"""
        if not raw_email:
            return None
        hashed = hash_email(raw_email)
        try:
            return cls.objects.get(email_hash=hashed)
        except cls.DoesNotExist:
            return None

    def has_perm(self, perm, obj=None):
        return self.is_admin or self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_admin or self.is_superuser

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False
    
    @property
    def role(self):
        """Return the user's primary role"""
        if self.is_admin and not self.is_sub_admin:
            return 'main_admin'
        if self.is_sub_admin:
            return 'sub_admin'
        if self.is_admin:
            return 'admin'
        if self.is_analyst:
            return 'analyst'
        return 'client'

    @property
    def is_main_admin(self):
        return self.is_admin and not self.is_sub_admin


class AuthToken(models.Model):
    """Tracks one-time login tokens (magic links) and password reset tokens"""
    user = models.ForeignKey(PseudonymousUser, on_delete=models.CASCADE, related_name='auth_tokens')
    token = models.CharField(max_length=128, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'core_authtoken'

    def is_valid(self):
        """Check if token is still valid"""
        return not self.used and timezone.now() < self.expires_at

    def __str__(self):
        return f"AuthToken for {self.user} (expires {self.expires_at})"
