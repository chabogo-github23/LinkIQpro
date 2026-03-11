# ShadowIQ Django Project Restructuring Guide

## Executive Summary

This guide provides a comprehensive plan to restructure your ShadowIQ Django project from a monolithic "core" app to a modular, SOLID-compliant architecture. The restructuring will improve maintainability, testability, and scalability.

---

## 1. Requirements Analysis: Domain Identification

Based on your codebase analysis, I've identified **6 main domains**:

| Domain | Current Location | Responsibilities |
|--------|-----------------|------------------|
| **Users** | `core/models.py`, `core/auth.py` | User management, authentication, authorization, roles |
| **Projects** | `core/models.py`, `core/views.py` | Project lifecycle, milestones, deliverables, files |
| **Payments** | `core/payment_manager.py`, `core/paystack_utils.py`, `core/views.py` | PayPal, Paystack integration, escrow, refunds |
| **Messaging** | `core/models.py`, `core/views.py` | Project chat, notifications, system messages |
| **Audit** | `core/models.py` | Activity logging, compliance tracking |
| **Negotiations** | `core/models.py`, `core/views.py` | Price proposals, terms agreement |

### Current Problems Identified

1. **God Object**: `core/views.py` (2153 lines) handles authentication, payments, projects, messaging
2. **Mixed Concerns**: Models contain business logic (e.g., `PseudonymousUser.set_password`, `Milestone.save`)
3. **Direct Gateway Access**: Views directly call `PayPalManager` and `paystack_payment`
4. **Tight Coupling**: Payment logic embedded in view functions
5. **No Service Layer**: Business rules scattered across views, models, and utilities

---

## 2. Proposed Modular App Structure

\`\`\`
shadowiq/
├── shadowiq/                    # Project settings
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py              # Common settings
│   │   ├── development.py       # Dev-specific
│   │   └── production.py        # Prod-specific
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── __init__.py
│   │
│   ├── users/                   # User & Auth Domain
│   │   ├── __init__.py
│   │   ├── models.py            # PseudonymousUser, AuthToken
│   │   ├── services.py          # AuthService, UserService
│   │   ├── selectors.py         # Query logic (get_by_email, etc.)
│   │   ├── forms.py
│   │   ├── views.py             # Login, register, dashboards
│   │   ├── urls.py
│   │   ├── decorators.py
│   │   ├── tokens.py
│   │   ├── admin.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_services.py
│   │       ├── test_selectors.py
│   │       └── test_views.py
│   │
│   ├── projects/                # Project Domain
│   │   ├── __init__.py
│   │   ├── models.py            # Project, Milestone, Deliverable, ProjectFile
│   │   ├── services.py          # ProjectService, MilestoneService
│   │   ├── selectors.py         # Query logic
│   │   ├── forms.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tests/
│   │
│   ├── payments/                # Payment Domain
│   │   ├── __init__.py
│   │   ├── models.py            # MilestonePayment
│   │   ├── services.py          # PaymentService (orchestrator)
│   │   ├── gateways/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # PaymentGatewayInterface (ABC)
│   │   │   ├── paypal.py        # PayPalGateway
│   │   │   └── paystack.py      # PaystackGateway
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── utils.py             # Currency conversion, validation
│   │   └── tests/
│   │
│   ├── messaging/               # Messaging Domain
│   │   ├── __init__.py
│   │   ├── models.py            # Message
│   │   ├── services.py          # MessagingService
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── audit/                   # Audit Domain
│   │   ├── __init__.py
│   │   ├── models.py            # AuditLog
│   │   ├── services.py          # AuditService
│   │   ├── middleware.py        # Auto-logging middleware
│   │   └── tests/
│   │
│   └── negotiations/            # Negotiation Domain
│       ├── __init__.py
│       ├── models.py            # ProjectNegotiation
│       ├── services.py          # NegotiationService
│       ├── views.py
│       ├── urls.py
│       └── tests/
│
├── common/                      # Shared utilities
│   ├── __init__.py
│   ├── mixins.py                # Reusable view mixins
│   ├── utils.py                 # get_client_ip, hash_email, etc.
│   ├── exceptions.py            # Custom exceptions
│   └── validators.py            # Shared validators
│
├── templates/
│   ├── base.html
│   ├── users/
│   ├── projects/
│   ├── payments/
│   └── ...
│
└── manage.py
\`\`\`

---

## 3. Implementation Guidance

### 3.1 Lean Models (Fields + Relationships Only)

#### Before (Current `PseudonymousUser`):
\`\`\`python
# core/models.py - PROBLEMATIC
class PseudonymousUser(models.Model):
    # Fields...
    
    def set_password(self, raw_password):
        """Hashes and sets a user's password"""
        self.password_hash = make_password(raw_password)
        self.save(update_fields=['password_hash'])  # ❌ Business logic + persistence

    def set_email(self, raw_email):
        """Hash and store the email address"""
        if raw_email:
            self.email_hash = hash_email(raw_email)
            self.email = None
            self.save(update_fields=['email_hash', 'email'])  # ❌ Business logic + persistence

    @classmethod
    def get_by_email(cls, raw_email):  # ❌ Query logic in model
        if not raw_email:
            return None
        hashed = hash_email(raw_email)
        try:
            return cls.objects.get(email_hash=hashed)
        except cls.DoesNotExist:
            return None
\`\`\`

#### After (Lean Model + Service + Selector):
\`\`\`python
# apps/users/models.py - CLEAN
class PseudonymousUser(models.Model):
    """User model - contains only fields and relationships"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alias = models.CharField(max_length=255, unique=True)
    email_hash = models.CharField(max_length=64, null=True, blank=True, unique=True)
    password_hash = models.CharField(max_length=255, null=True, blank=True)
    magic_token = models.CharField(max_length=255, unique=True, null=True, blank=True)
    magic_token_expires = models.DateTimeField(null=True, blank=True)
    
    is_admin = models.BooleanField(default=False)
    is_analyst = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.alias

    # ✅ Only simple computed properties allowed
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False
\`\`\`

\`\`\`python
# apps/users/selectors.py - QUERY LOGIC
from django.db.models import Q
from common.utils import hash_email
from .models import PseudonymousUser


def get_user_by_id(user_id: str) -> PseudonymousUser | None:
    """Fetch user by UUID"""
    try:
        return PseudonymousUser.objects.get(id=user_id)
    except PseudonymousUser.DoesNotExist:
        return None


def get_user_by_alias(alias: str) -> PseudonymousUser | None:
    """Fetch user by alias"""
    try:
        return PseudonymousUser.objects.get(alias=alias)
    except PseudonymousUser.DoesNotExist:
        return None


def get_user_by_email(email: str) -> PseudonymousUser | None:
    """Fetch user by email (hashed lookup)"""
    if not email:
        return None
    email_hash = hash_email(email)
    try:
        return PseudonymousUser.objects.get(email_hash=email_hash)
    except PseudonymousUser.DoesNotExist:
        return None


def get_user_by_magic_token(token: str) -> PseudonymousUser | None:
    """Fetch user by magic token"""
    try:
        return PseudonymousUser.objects.get(magic_token=token)
    except PseudonymousUser.DoesNotExist:
        return None


def get_all_analysts() -> list[PseudonymousUser]:
    """Get all active analysts"""
    return list(PseudonymousUser.objects.filter(is_analyst=True, is_active=True))


def get_all_admins() -> list[PseudonymousUser]:
    """Get all active admins"""
    return list(PseudonymousUser.objects.filter(is_admin=True, is_active=True))


def user_exists_by_alias(alias: str) -> bool:
    """Check if alias is taken"""
    return PseudonymousUser.objects.filter(alias=alias).exists()


def user_exists_by_email(email: str) -> bool:
    """Check if email is registered"""
    email_hash = hash_email(email)
    return PseudonymousUser.objects.filter(email_hash=email_hash).exists()
\`\`\`

\`\`\`python
# apps/users/services.py - BUSINESS LOGIC
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Tuple

from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from common.utils import hash_email
from common.exceptions import ValidationError, AuthenticationError
from .models import PseudonymousUser
from . import selectors


@dataclass
class UserCreateResult:
    user: Optional[PseudonymousUser]
    error: Optional[str]


class UserService:
    """Handles user creation and management"""
    
    @staticmethod
    def create_user(
        alias: str,
        email: str,
        password: str,
        is_admin: bool = False,
        is_analyst: bool = False
    ) -> UserCreateResult:
        """
        Create a new user with proper validation.
        Returns UserCreateResult with user or error.
        """
        # Validation
        alias = alias.strip() if alias else ""
        email = email.strip().lower() if email else ""
        
        if len(alias) < 3:
            return UserCreateResult(None, "Alias must be at least 3 characters long.")
        
        if not email or '@' not in email:
            return UserCreateResult(None, "A valid email address is required.")
        
        if not password or len(password) < 6:
            return UserCreateResult(None, "Password must be at least 6 characters long.")
        
        if selectors.user_exists_by_alias(alias):
            return UserCreateResult(None, "This alias is already taken.")
        
        if selectors.user_exists_by_email(email):
            return UserCreateResult(None, "This email is already registered.")
        
        # Create user
        try:
            user = PseudonymousUser.objects.create(
                alias=alias,
                email_hash=hash_email(email),
                password_hash=make_password(password),
                is_admin=is_admin,
                is_analyst=is_analyst,
                is_staff=is_admin,
                is_superuser=is_admin,
            )
            return UserCreateResult(user, None)
        except Exception as e:
            return UserCreateResult(None, f"Registration failed: {str(e)}")
    
    @staticmethod
    def update_password(user: PseudonymousUser, new_password: str) -> None:
        """Update user's password"""
        if len(new_password) < 6:
            raise ValidationError("Password must be at least 6 characters long.")
        
        user.password_hash = make_password(new_password)
        user.save(update_fields=['password_hash'])
    
    @staticmethod
    def update_email(user: PseudonymousUser, new_email: str) -> None:
        """Update user's email (stored as hash)"""
        if not new_email or '@' not in new_email:
            raise ValidationError("A valid email is required.")
        
        new_email = new_email.strip().lower()
        email_hash = hash_email(new_email)
        
        # Check if email already used by another user
        existing = selectors.get_user_by_email(new_email)
        if existing and existing.id != user.id:
            raise ValidationError("This email is already registered.")
        
        user.email_hash = email_hash
        user.save(update_fields=['email_hash'])
    
    @staticmethod
    def deactivate_user(user: PseudonymousUser) -> None:
        """Deactivate a user account"""
        user.is_active = False
        user.save(update_fields=['is_active'])
    
    @staticmethod
    def activate_user(user: PseudonymousUser) -> None:
        """Activate a user account"""
        user.is_active = True
        user.save(update_fields=['is_active'])


class AuthService:
    """Handles authentication operations"""
    
    MAGIC_TOKEN_EXPIRY_HOURS = 24
    
    @staticmethod
    def authenticate(alias: str, password: str) -> Optional[PseudonymousUser]:
        """
        Authenticate user by alias and password.
        Returns user if successful, None otherwise.
        """
        user = selectors.get_user_by_alias(alias)
        if not user:
            return None
        
        if not user.password_hash:
            return None
        
        if not check_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    @staticmethod
    def generate_magic_token(user: PseudonymousUser) -> str:
        """Generate and store a magic link token"""
        token = secrets.token_urlsafe(32)
        expires = timezone.now() + timedelta(hours=AuthService.MAGIC_TOKEN_EXPIRY_HOURS)
        
        user.magic_token = token
        user.magic_token_expires = expires
        user.save(update_fields=['magic_token', 'magic_token_expires'])
        
        return token
    
    @staticmethod
    def verify_magic_token(token: str) -> Optional[PseudonymousUser]:
        """Verify magic token and return user if valid"""
        user = selectors.get_user_by_magic_token(token)
        if not user:
            return None
        
        if not user.magic_token_expires or user.magic_token_expires < timezone.now():
            return None
        
        # Invalidate token after use
        user.magic_token = None
        user.magic_token_expires = None
        user.last_login = timezone.now()
        user.save(update_fields=['magic_token', 'magic_token_expires', 'last_login'])
        
        return user
    
    @staticmethod
    def check_email_match(user: PseudonymousUser, email: str) -> bool:
        """Check if provided email matches user's stored hash"""
        if not email or not user.email_hash:
            return False
        return hash_email(email.strip().lower()) == user.email_hash
\`\`\`

### 3.2 Payment Service with Gateway Abstraction

#### Before (Direct Gateway Calls in Views):
\`\`\`python
# core/views.py - PROBLEMATIC
def handle_paypal_milestone_payment(request, project, milestones, total_amount):
    try:
        # ❌ Direct PayPal API interaction in view
        order_id, approval_url = PayPalManager.create_milestone_order(
            project, milestones, total_amount, request
        )
        
        first_milestone = milestones.first()
        if first_milestone:
            # ❌ Business logic in view
            first_milestone.paypal_order_id = order_id
            first_milestone.payment_status = 'processing'
            first_milestone.gateway_used = 'paypal'
            first_milestone.save()
        # ...
\`\`\`

#### After (Gateway Interface + Service):
\`\`\`python
# apps/payments/gateways/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from decimal import Decimal


@dataclass
class PaymentInitResult:
    success: bool
    redirect_url: Optional[str] = None
    reference: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class PaymentVerifyResult:
    success: bool
    is_successful: bool = False
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    reference: Optional[str] = None
    error: Optional[str] = None
    gateway_response: Optional[str] = None


@dataclass
class PaymentCaptureResult:
    success: bool
    error: Optional[str] = None
    capture_id: Optional[str] = None


class PaymentGatewayInterface(ABC):
    """Abstract base class for payment gateways"""
    
    @property
    @abstractmethod
    def gateway_name(self) -> str:
        """Return gateway identifier"""
        pass
    
    @abstractmethod
    def initialize_payment(
        self,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,
        metadata: Dict[str, Any],
        email: Optional[str] = None
    ) -> PaymentInitResult:
        """Initialize a payment and return redirect URL"""
        pass
    
    @abstractmethod
    def verify_payment(self, reference: str) -> PaymentVerifyResult:
        """Verify a payment after callback"""
        pass
    
    @abstractmethod
    def capture_payment(self, authorization_id: str) -> PaymentCaptureResult:
        """Capture authorized funds (for escrow gateways)"""
        pass
    
    @abstractmethod
    def refund_payment(
        self,
        reference: str,
        amount: Optional[Decimal] = None
    ) -> PaymentCaptureResult:
        """Refund a captured payment"""
        pass
\`\`\`

\`\`\`python
# apps/payments/gateways/paypal.py
import requests
from decimal import Decimal
from typing import Dict, Any, Optional
from django.conf import settings

from .base import (
    PaymentGatewayInterface,
    PaymentInitResult,
    PaymentVerifyResult,
    PaymentCaptureResult,
)


class PayPalGateway(PaymentGatewayInterface):
    """PayPal payment gateway implementation"""
    
    API_BASE = "https://api-m.sandbox.paypal.com"  # Change for production
    
    @property
    def gateway_name(self) -> str:
        return "paypal"
    
    def _get_access_token(self) -> str:
        """Get OAuth access token from PayPal"""
        response = requests.post(
            f"{self.API_BASE}/v1/oauth2/token",
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"PayPal Auth Error: {response.text}")
        
        return response.json()["access_token"]
    
    def initialize_payment(
        self,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,
        metadata: Dict[str, Any],
        email: Optional[str] = None
    ) -> PaymentInitResult:
        """Create PayPal order with authorization intent"""
        try:
            token = self._get_access_token()
            
            payload = {
                "intent": "AUTHORIZE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}",
                    },
                    "description": metadata.get("description", "Payment"),
                    "custom_id": metadata.get("custom_id", ""),
                    "invoice_id": metadata.get("invoice_id", ""),
                }],
                "application_context": {
                    "brand_name": "ShadowIQ Projects",
                    "landing_page": "LOGIN",
                    "user_action": "CONTINUE",
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                },
            }
            
            response = requests.post(
                f"{self.API_BASE}/v2/checkout/orders",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json=payload,
                timeout=30
            )
            
            if response.status_code not in (200, 201):
                error = response.json().get('message', 'Unknown error')
                return PaymentInitResult(success=False, error=error)
            
            data = response.json()
            approval_url = next(
                (link["href"] for link in data["links"] if link["rel"] == "approve"),
                None
            )
            
            return PaymentInitResult(
                success=True,
                redirect_url=approval_url,
                reference=data["id"],
                metadata={"order_id": data["id"]}
            )
            
        except Exception as e:
            return PaymentInitResult(success=False, error=str(e))
    
    def verify_payment(self, reference: str) -> PaymentVerifyResult:
        """Authorize PayPal order and hold funds"""
        try:
            token = self._get_access_token()
            
            response = requests.post(
                f"{self.API_BASE}/v2/checkout/orders/{reference}/authorize",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=30
            )
            
            if response.status_code not in (200, 201):
                error = response.json().get('message', 'Authorization failed')
                return PaymentVerifyResult(success=False, error=error)
            
            data = response.json()
            
            try:
                auth = data["purchase_units"][0]["payments"]["authorizations"][0]
                auth_id = auth["id"]
                status = auth["status"]
                amount = Decimal(auth["amount"]["value"])
                currency = auth["amount"]["currency_code"]
                
                return PaymentVerifyResult(
                    success=True,
                    is_successful=status in ["CREATED", "PENDING"],
                    amount=amount,
                    currency=currency,
                    reference=auth_id,
                    gateway_response=status
                )
            except (KeyError, IndexError):
                return PaymentVerifyResult(
                    success=False,
                    error="Invalid PayPal response structure"
                )
                
        except Exception as e:
            return PaymentVerifyResult(success=False, error=str(e))
    
    def capture_payment(self, authorization_id: str) -> PaymentCaptureResult:
        """Capture authorized PayPal funds"""
        try:
            token = self._get_access_token()
            
            response = requests.post(
                f"{self.API_BASE}/v2/payments/authorizations/{authorization_id}/capture",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=30
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                return PaymentCaptureResult(
                    success=True,
                    capture_id=data.get("id")
                )
            
            error = response.json().get('message', 'Capture failed')
            return PaymentCaptureResult(success=False, error=error)
            
        except Exception as e:
            return PaymentCaptureResult(success=False, error=str(e))
    
    def refund_payment(
        self,
        reference: str,
        amount: Optional[Decimal] = None
    ) -> PaymentCaptureResult:
        """Refund a captured PayPal payment"""
        try:
            token = self._get_access_token()
            
            payload = {}
            if amount:
                payload["amount"] = {
                    "currency_code": "USD",
                    "value": f"{amount:.2f}"
                }
            
            response = requests.post(
                f"{self.API_BASE}/v2/payments/captures/{reference}/refund",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json=payload,
                timeout=30
            )
            
            if response.status_code in (200, 201):
                return PaymentCaptureResult(success=True)
            
            error = response.json().get('message', 'Refund failed')
            return PaymentCaptureResult(success=False, error=error)
            
        except Exception as e:
            return PaymentCaptureResult(success=False, error=str(e))
\`\`\`

\`\`\`python
# apps/payments/gateways/paystack.py
import requests
from decimal import Decimal
from typing import Dict, Any, Optional
from django.conf import settings

from .base import (
    PaymentGatewayInterface,
    PaymentInitResult,
    PaymentVerifyResult,
    PaymentCaptureResult,
)


class PaystackGateway(PaymentGatewayInterface):
    """Paystack payment gateway implementation"""
    
    API_BASE = "https://api.paystack.co"
    
    # Currencies that use minor units (cents)
    CENT_CURRENCIES = ['USD', 'KES', 'GHS', 'ZAR', 'GBP', 'EUR']
    
    @property
    def gateway_name(self) -> str:
        return "paystack"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
    
    def _to_minor_units(self, amount: Decimal, currency: str) -> int:
        """Convert to smallest currency unit"""
        if currency == 'NGN':
            return int(amount)  # Naira stored as-is
        if currency in self.CENT_CURRENCIES:
            return int(amount)  # Amount already in minor units
        return int(amount)
    
    def _from_minor_units(self, amount: int, currency: str) -> Decimal:
        """Convert from smallest currency unit"""
        if currency == 'NGN':
            return Decimal(amount)
        if currency in self.CENT_CURRENCIES:
            return Decimal(amount) / 100
        return Decimal(amount) / 100
    
    def initialize_payment(
        self,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,  # Not used by Paystack but kept for interface
        metadata: Dict[str, Any],
        email: Optional[str] = None
    ) -> PaymentInitResult:
        """Initialize Paystack payment"""
        if not email:
            return PaymentInitResult(
                success=False,
                error="Email is required for Paystack payments"
            )
        
        try:
            amount_minor = self._to_minor_units(amount, currency)
            
            payload = {
                "email": email,
                "amount": amount_minor,
                "currency": currency,
                "callback_url": return_url,
                "metadata": metadata
            }
            
            response = requests.post(
                f"{self.API_BASE}/transaction/initialize",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get("status"):
                return PaymentInitResult(
                    success=True,
                    redirect_url=result["data"]["authorization_url"],
                    reference=result["data"]["reference"],
                    metadata={"access_code": result["data"]["access_code"]}
                )
            
            error = result.get("message", "Payment initialization failed")
            return PaymentInitResult(success=False, error=error)
            
        except Exception as e:
            return PaymentInitResult(success=False, error=str(e))
    
    def verify_payment(self, reference: str) -> PaymentVerifyResult:
        """Verify Paystack payment"""
        try:
            response = requests.get(
                f"{self.API_BASE}/transaction/verify/{reference}",
                headers=self._get_headers(),
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get("status"):
                data = result["data"]
                currency = data.get("currency", "USD")
                
                return PaymentVerifyResult(
                    success=True,
                    is_successful=data.get("status") == "success",
                    amount=self._from_minor_units(data.get("amount", 0), currency),
                    currency=currency,
                    reference=data.get("reference"),
                    gateway_response=data.get("gateway_response")
                )
            
            error = result.get("message", "Verification failed")
            return PaymentVerifyResult(success=False, error=error)
            
        except Exception as e:
            return PaymentVerifyResult(success=False, error=str(e))
    
    def capture_payment(self, authorization_id: str) -> PaymentCaptureResult:
        """Paystack auto-captures, so this is a no-op"""
        return PaymentCaptureResult(success=True)
    
    def refund_payment(
        self,
        reference: str,
        amount: Optional[Decimal] = None
    ) -> PaymentCaptureResult:
        """Refund a Paystack payment"""
        try:
            payload = {"transaction": reference}
            
            if amount:
                # Assume USD for now, should be passed in
                payload["amount"] = self._to_minor_units(amount, "USD")
            
            response = requests.post(
                f"{self.API_BASE}/refund",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get("status"):
                return PaymentCaptureResult(success=True)
            
            error = result.get("message", "Refund failed")
            return PaymentCaptureResult(success=False, error=error)
            
        except Exception as e:
            return PaymentCaptureResult(success=False, error=str(e))
\`\`\`

\`\`\`python
# apps/payments/services.py
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List, Dict, Any
from django.utils import timezone

from apps.projects.models import Project, Milestone
from apps.audit.services import AuditService

from .gateways.base import PaymentGatewayInterface
from .gateways.paypal import PayPalGateway
from .gateways.paystack import PaystackGateway


@dataclass
class MilestonePaymentResult:
    success: bool
    redirect_url: Optional[str] = None
    reference: Optional[str] = None
    error: Optional[str] = None
    milestone_count: int = 0
    total_amount: Decimal = Decimal("0")


class PaymentService:
    """
    Orchestrates payment operations across different gateways.
    Single Responsibility: Payment coordination and milestone payment state management.
    Open/Closed: New gateways can be added without modifying this class.
    """
    
    GATEWAYS: Dict[str, PaymentGatewayInterface] = {
        'paypal': PayPalGateway(),
        'paystack': PaystackGateway(),
    }
    
    @classmethod
    def get_gateway(cls, gateway_name: str) -> Optional[PaymentGatewayInterface]:
        """Get gateway instance by name"""
        return cls.GATEWAYS.get(gateway_name)
    
    @classmethod
    def register_gateway(cls, name: str, gateway: PaymentGatewayInterface) -> None:
        """Register a new payment gateway (Open/Closed principle)"""
        cls.GATEWAYS[name] = gateway
    
    @classmethod
    def initialize_milestone_payment(
        cls,
        project: Project,
        milestones: List[Milestone],
        gateway_name: str,
        return_url: str,
        cancel_url: str,
        user,
        email: Optional[str] = None,
        currency: str = "USD"
    ) -> MilestonePaymentResult:
        """
        Initialize payment for one or more milestones.
        Handles gateway selection, validation, and state management.
        """
        # Validate gateway
        gateway = cls.get_gateway(gateway_name)
        if not gateway:
            return MilestonePaymentResult(
                success=False,
                error=f"Unknown payment gateway: {gateway_name}"
            )
        
        # Validate milestones
        errors = cls._validate_milestones(milestones)
        if errors:
            return MilestonePaymentResult(
                success=False,
                error="; ".join(errors)
            )
        
        # Calculate total
        total_amount = sum(m.amount for m in milestones)
        milestone_ids = [str(m.id) for m in milestones]
        
        # Build metadata
        metadata = {
            "project_id": str(project.project_id),
            "milestone_ids": milestone_ids,
            "payment_type": "milestone_batch" if len(milestones) > 1 else "milestone",
            "description": f"Payment for {len(milestones)} milestone(s) - Project {project.project_id}",
            "custom_id": f"project_{project.project_id}",
            "invoice_id": f"milestones_{'_'.join(milestone_ids)}",
        }
        
        # Reset any previous processing state
        cls._reset_milestone_payment_state(milestones)
        
        # Initialize with gateway
        result = gateway.initialize_payment(
            amount=total_amount,
            currency=currency,
            return_url=return_url,
            cancel_url=cancel_url,
            metadata=metadata,
            email=email
        )
        
        if not result.success:
            AuditService.log_action(
                user=user,
                project=project,
                action=f"{gateway_name}_payment_init_failed",
                details={"error": result.error}
            )
            return MilestonePaymentResult(
                success=False,
                error=result.error
            )
        
        # Update milestone state to processing
        cls._set_milestones_processing(
            milestones=milestones,
            gateway_name=gateway_name,
            reference=result.reference
        )
        
        return MilestonePaymentResult(
            success=True,
            redirect_url=result.redirect_url,
            reference=result.reference,
            milestone_count=len(milestones),
            total_amount=total_amount
        )
    
    @classmethod
    def verify_and_complete_payment(
        cls,
        project: Project,
        reference: str,
        gateway_name: str,
        user
    ) -> MilestonePaymentResult:
        """Verify payment and update milestone status"""
        gateway = cls.get_gateway(gateway_name)
        if not gateway:
            return MilestonePaymentResult(success=False, error="Unknown gateway")
        
        # Verify with gateway
        result = gateway.verify_payment(reference)
        
        if not result.success or not result.is_successful:
            # Payment failed - reset milestones
            cls._handle_payment_failure(project, reference, gateway_name, user, result.error)
            return MilestonePaymentResult(
                success=False,
                error=result.error or "Payment verification failed"
            )
        
        # Payment successful - update milestones
        milestones = cls._get_milestones_by_reference(project, reference, gateway_name)
        
        for milestone in milestones:
            milestone.payment_status = 'funded'
            milestone.funded_at = timezone.now()
            
            # Store auth ID for PayPal (needed for capture later)
            if gateway_name == 'paypal' and result.reference:
                milestone.paypal_auth_id = result.reference
            
            milestone.save()
        
        AuditService.log_action(
            user=user,
            project=project,
            action=f"{gateway_name}_payment_success",
            details={
                "reference": reference,
                "milestone_count": len(milestones),
                "amount": str(result.amount),
                "currency": result.currency
            }
        )
        
        return MilestonePaymentResult(
            success=True,
            milestone_count=len(milestones),
            total_amount=result.amount or Decimal("0")
        )
    
    @classmethod
    def release_milestone_payment(
        cls,
        milestone: Milestone,
        user
    ) -> MilestonePaymentResult:
        """Release/capture payment for an approved milestone"""
        if not milestone.is_releasable:
            return MilestonePaymentResult(
                success=False,
                error="Milestone not ready for release"
            )
        
        gateway = cls.get_gateway(milestone.gateway_used)
        if not gateway:
            return MilestonePaymentResult(
                success=False,
                error="Unknown payment gateway"
            )
        
        # For PayPal, capture the authorization
        if milestone.gateway_used == 'paypal' and milestone.paypal_auth_id:
            result = gateway.capture_payment(milestone.paypal_auth_id)
            
            if not result.success:
                return MilestonePaymentResult(
                    success=False,
                    error=result.error
                )
        
        # Update milestone status
        milestone.payment_status = 'released'
        milestone.released_at = timezone.now()
        milestone.save()
        
        AuditService.log_action(
            user=user,
            project=milestone.project,
            milestone=milestone,
            action=f"{milestone.gateway_used}_payment_released",
            details={
                "title": milestone.title,
                "amount": str(milestone.amount)
            }
        )
        
        return MilestonePaymentResult(
            success=True,
            total_amount=milestone.amount
        )
    
    # Private helper methods
    @staticmethod
    def _validate_milestones(milestones: List[Milestone]) -> List[str]:
        """Validate milestones are ready for payment"""
        errors = []
        
        if not milestones:
            return ["No milestones provided for payment"]
        
        for m in milestones:
            if m.payment_status not in ['unfunded', 'processing']:
                errors.append(f"Milestone '{m.title}' is already funded")
            if m.amount <= 0:
                errors.append(f"Milestone '{m.title}' has invalid amount")
        
        return errors
    
    @staticmethod
    def _reset_milestone_payment_state(milestones: List[Milestone]) -> None:
        """Reset milestones that were stuck in processing"""
        for m in milestones:
            if m.payment_status == 'processing':
                m.payment_status = 'unfunded'
                m.gateway_used = None
                m.paypal_order_id = None
                m.paypal_auth_id = None
                m.paystack_reference = None
                m.save()
    
    @staticmethod
    def _set_milestones_processing(
        milestones: List[Milestone],
        gateway_name: str,
        reference: str
    ) -> None:
        """Mark milestones as processing"""
        for i, m in enumerate(milestones):
            m.payment_status = 'processing'
            m.gateway_used = gateway_name
            
            if gateway_name == 'paypal':
                if i == 0:  # First milestone stores the order ID
                    m.paypal_order_id = reference
            elif gateway_name == 'paystack':
                m.paystack_reference = reference
            
            m.save()
    
    @staticmethod
    def _get_milestones_by_reference(
        project: Project,
        reference: str,
        gateway_name: str
    ) -> List[Milestone]:
        """Get milestones by payment reference"""
        if gateway_name == 'paypal':
            return list(project.milestones.filter(
                payment_status='processing',
                gateway_used='paypal'
            ))
        elif gateway_name == 'paystack':
            return list(project.milestones.filter(
                paystack_reference=reference,
                payment_status='processing'
            ))
        return []
    
    @classmethod
    def _handle_payment_failure(
        cls,
        project: Project,
        reference: str,
        gateway_name: str,
        user,
        error: Optional[str]
    ) -> None:
        """Handle payment failure - reset milestones and log"""
        milestones = cls._get_milestones_by_reference(project, reference, gateway_name)
        
        for m in milestones:
            m.payment_status = 'unfunded'
            m.gateway_used = None
            m.paypal_order_id = None
            m.paypal_auth_id = None
            m.paystack_reference = None
            m.paystack_currency = None
            m.save()
        
        AuditService.log_action(
            user=user,
            project=project,
            action=f"{gateway_name}_payment_failed",
            details={
                "reference": reference,
                "error": error,
                "milestone_count": len(milestones)
            }
        )
\`\`\`

### 3.3 Refactored Views (Thin Controllers)

#### Before (Fat View):
\`\`\`python
# core/views.py - 100+ lines per view
def handle_paypal_milestone_payment(request, project, milestones, total_amount):
    try:
        for milestone in milestones:
            if milestone.payment_status == "processing":
                milestone.payment_status = "unfunded"
                milestone.gateway_used = None
                # ... more reset logic

        order_id, approval_url = PayPalManager.create_milestone_order(...)
        
        first_milestone = milestones.first()
        if first_milestone:
            first_milestone.paypal_order_id = order_id
            # ... more business logic

        return JsonResponse({...})
    except Exception as e:
        milestones.update(...)  # More business logic
        AuditLog.objects.create(...)
        return JsonResponse({"error": str(e)}, status=500)
\`\`\`

#### After (Thin View):
\`\`\`python
# apps/payments/views.py
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from apps.users.decorators import pseudonymous_user_required
from apps.projects.models import Project
from .services import PaymentService


@pseudonymous_user_required
@require_POST
def create_milestone_payment(request, project_id):
    """
    Initialize milestone payment.
    View only handles HTTP concerns - all business logic in PaymentService.
    """
    project = get_object_or_404(Project, project_id=project_id)
    
    # Authorization check
    if project.client_id != request.user.id:
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    # Parse request
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    gateway = data.get("gateway")
    milestone_ids = data.get("milestone_ids", [])
    email = data.get("user_email")
    currency = data.get("currency", "USD")
    
    # Validate gateway
    if gateway not in ['paypal', 'paystack']:
        return JsonResponse({"error": "Invalid payment gateway"}, status=400)
    
    # Get milestones
    if milestone_ids:
        milestones = list(project.milestones.filter(
            id__in=milestone_ids,
            payment_status__in=['unfunded', 'processing']
        ))
    else:
        milestones = list(project.milestones.filter(
            payment_status__in=['unfunded', 'processing']
        ))
    
    if not milestones:
        return JsonResponse({"error": "No milestones to pay for"}, status=400)
    
    # Build URLs
    return_url = request.build_absolute_uri(
        f"/project/{project.project_id}/payment/success/?method={gateway}"
    )
    cancel_url = request.build_absolute_uri(
        f"/project/{project.project_id}/payment/cancel/"
    )
    
    # Delegate to service
    result = PaymentService.initialize_milestone_payment(
        project=project,
        milestones=milestones,
        gateway_name=gateway,
        return_url=return_url,
        cancel_url=cancel_url,
        user=request.user,
        email=email,
        currency=currency
    )
    
    # Return response
    if result.success:
        return JsonResponse({
            "success": True,
            "redirect_url": result.redirect_url,
            "reference": result.reference,
            "milestone_count": result.milestone_count,
            "total_amount": float(result.total_amount)
        })
    else:
        return JsonResponse({
            "success": False,
            "error": result.error
        }, status=400)


@pseudonymous_user_required
def payment_success(request, project_id):
    """Handle payment success callback"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if project.client_id != request.user.id:
        return render(request, "payments/access_denied.html", status=403)
    
    # Determine gateway and reference
    method = request.GET.get("method", "").lower()
    reference = request.GET.get("reference") or request.GET.get("token")
    
    if method == "paystack":
        gateway_name = "paystack"
    elif method == "paypal":
        gateway_name = "paypal"
    else:
        return redirect('payments:milestone_payment', project_id=project.project_id)
    
    # Delegate to service
    result = PaymentService.verify_and_complete_payment(
        project=project,
        reference=reference,
        gateway_name=gateway_name,
        user=request.user
    )
    
    if result.success:
        return render(request, "payments/success.html", {
            "project": project,
            "milestone_count": result.milestone_count,
            "total_amount": result.total_amount
        })
    else:
        return render(request, "payments/failed.html", {
            "project": project,
            "error": result.error,
            "can_retry": True
        })
\`\`\`

---

## 4. Testing Strategy

### 4.1 Service Testing (Independent of Django Views)

\`\`\`python
# apps/users/tests/test_services.py
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from apps.users.services import UserService, AuthService
from apps.users.models import PseudonymousUser


class TestUserService:
    """Test UserService in isolation"""
    
    @pytest.mark.django_db
    def test_create_user_success(self):
        """Test successful user creation"""
        result = UserService.create_user(
            alias="testuser",
            email="test@example.com",
            password="securepass123"
        )
        
        assert result.user is not None
        assert result.error is None
        assert result.user.alias == "testuser"
        assert result.user.email_hash is not None
        assert result.user.password_hash is not None
    
    @pytest.mark.django_db
    def test_create_user_short_alias(self):
        """Test validation for short alias"""
        result = UserService.create_user(
            alias="ab",
            email="test@example.com",
            password="securepass123"
        )
        
        assert result.user is None
        assert "at least 3 characters" in result.error
    
    @pytest.mark.django_db
    def test_create_user_invalid_email(self):
        """Test validation for invalid email"""
        result = UserService.create_user(
            alias="testuser",
            email="invalid-email",
            password="securepass123"
        )
        
        assert result.user is None
        assert "valid email" in result.error
    
    @pytest.mark.django_db
    def test_create_user_duplicate_alias(self):
        """Test duplicate alias handling"""
        # Create first user
        UserService.create_user(
            alias="existinguser",
            email="first@example.com",
            password="password123"
        )
        
        # Try to create duplicate
        result = UserService.create_user(
            alias="existinguser",
            email="second@example.com",
            password="password123"
        )
        
        assert result.user is None
        assert "already taken" in result.error


class TestAuthService:
    """Test AuthService in isolation"""
    
    @pytest.mark.django_db
    def test_authenticate_success(self):
        """Test successful authentication"""
        # Setup
        UserService.create_user(
            alias="authuser",
            email="auth@example.com",
            password="mypassword"
        )
        
        # Test
        user = AuthService.authenticate("authuser", "mypassword")
        
        assert user is not None
        assert user.alias == "authuser"
    
    @pytest.mark.django_db
    def test_authenticate_wrong_password(self):
        """Test authentication with wrong password"""
        UserService.create_user(
            alias="authuser",
            email="auth@example.com",
            password="mypassword"
        )
        
        user = AuthService.authenticate("authuser", "wrongpassword")
        
        assert user is None
    
    @pytest.mark.django_db
    def test_magic_token_flow(self):
        """Test magic token generation and verification"""
        result = UserService.create_user(
            alias="magicuser",
            email="magic@example.com",
            password="password123"
        )
        user = result.user
        
        # Generate token
        token = AuthService.generate_magic_token(user)
        assert token is not None
        
        # Verify token
        verified_user = AuthService.verify_magic_token(token)
        assert verified_user is not None
        assert verified_user.id == user.id
        
        # Token should be invalidated after use
        second_verify = AuthService.verify_magic_token(token)
        assert second_verify is None
\`\`\`

\`\`\`python
# apps/payments/tests/test_services.py
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.utils import timezone

from apps.payments.services import PaymentService
from apps.payments.gateways.base import PaymentInitResult, PaymentVerifyResult


class TestPaymentService:
    """Test PaymentService with mocked gateways"""
    
    @pytest.mark.django_db
    def test_initialize_payment_success(self, project_with_milestones):
        """Test successful payment initialization"""
        project, milestones, user = project_with_milestones
        
        # Mock the gateway
        mock_result = PaymentInitResult(
            success=True,
            redirect_url="https://paypal.com/checkout",
            reference="ORDER123"
        )
        
        with patch.object(
            PaymentService.GATEWAYS['paypal'],
            'initialize_payment',
            return_value=mock_result
        ):
            result = PaymentService.initialize_milestone_payment(
                project=project,
                milestones=milestones,
                gateway_name='paypal',
                return_url="http://test.com/success",
                cancel_url="http://test.com/cancel",
                user=user
            )
        
        assert result.success is True
        assert result.redirect_url == "https://paypal.com/checkout"
        assert result.milestone_count == len(milestones)
    
    @pytest.mark.django_db
    def test_initialize_payment_invalid_gateway(self, project_with_milestones):
        """Test error for unknown gateway"""
        project, milestones, user = project_with_milestones
        
        result = PaymentService.initialize_milestone_payment(
            project=project,
            milestones=milestones,
            gateway_name='invalid_gateway',
            return_url="http://test.com/success",
            cancel_url="http://test.com/cancel",
            user=user
        )
        
        assert result.success is False
        assert "Unknown payment gateway" in result.error
    
    @pytest.mark.django_db
    def test_verify_payment_success(self, project_with_processing_milestones):
        """Test successful payment verification"""
        project, milestones, user = project_with_processing_milestones
        
        mock_result = PaymentVerifyResult(
            success=True,
            is_successful=True,
            amount=Decimal("100.00"),
            currency="USD",
            reference="AUTH123"
        )
        
        with patch.object(
            PaymentService.GATEWAYS['paypal'],
            'verify_payment',
            return_value=mock_result
        ):
            result = PaymentService.verify_and_complete_payment(
                project=project,
                reference="ORDER123",
                gateway_name='paypal',
                user=user
            )
        
        assert result.success is True
        
        # Check milestones were updated
        for m in milestones:
            m.refresh_from_db()
            assert m.payment_status == 'funded'


@pytest.fixture
def project_with_milestones(db):
    """Create a project with unfunded milestones for testing"""
    from apps.users.services import UserService
    from apps.projects.models import Project, Milestone
    
    user_result = UserService.create_user(
        alias="testclient",
        email="client@test.com",
        password="password123"
    )
    user = user_result.user
    
    project = Project.objects.create(
        client=user,
        title="Test Project",
        description="Test description",
        stage="proposal",
        support_type="analysis_plan",
        research_area="Statistics"
    )
    
    milestones = [
        Milestone.objects.create(
            project=project,
            title=f"Milestone {i}",
            description=f"Description {i}",
            amount=Decimal("50.00"),
            due_date=timezone.now().date()
        )
        for i in range(2)
    ]
    
    return project, milestones, user
\`\`\`

### 4.2 Gateway Testing (Unit Tests with Mocked HTTP)

\`\`\`python
# apps/payments/tests/test_gateways.py
import pytest
import responses
from decimal import Decimal

from apps.payments.gateways.paypal import PayPalGateway
from apps.payments.gateways.paystack import PaystackGateway


class TestPayPalGateway:
    """Test PayPal gateway with mocked HTTP responses"""
    
    @responses.activate
    def test_initialize_payment_success(self, settings):
        """Test successful PayPal order creation"""
        settings.PAYPAL_CLIENT_ID = "test_client_id"
        settings.PAYPAL_SECRET = "test_secret"
        
        # Mock OAuth token
        responses.add(
            responses.POST,
            "https://api-m.sandbox.paypal.com/v1/oauth2/token",
            json={"access_token": "test_token"},
            status=200
        )
        
        # Mock order creation
        responses.add(
            responses.POST,
            "https://api-m.sandbox.paypal.com/v2/checkout/orders",
            json={
                "id": "ORDER123",
                "links": [
                    {"rel": "approve", "href": "https://paypal.com/checkout/ORDER123"}
                ]
            },
            status=201
        )
        
        gateway = PayPalGateway()
        result = gateway.initialize_payment(
            amount=Decimal("100.00"),
            currency="USD",
            return_url="http://test.com/success",
            cancel_url="http://test.com/cancel",
            metadata={"description": "Test payment"}
        )
        
        assert result.success is True
        assert result.reference == "ORDER123"
        assert "paypal.com/checkout" in result.redirect_url


class TestPaystackGateway:
    """Test Paystack gateway with mocked HTTP responses"""
    
    @responses.activate
    def test_initialize_payment_success(self, settings):
        """Test successful Paystack transaction initialization"""
        settings.PAYSTACK_SECRET_KEY = "test_secret_key"
        
        responses.add(
            responses.POST,
            "https://api.paystack.co/transaction/initialize",
            json={
                "status": True,
                "data": {
                    "authorization_url": "https://paystack.com/pay/abc123",
                    "reference": "REF123",
                    "access_code": "ACC123"
                }
            },
            status=200
        )
        
        gateway = PaystackGateway()
        result = gateway.initialize_payment(
            amount=Decimal("100.00"),
            currency="USD",
            return_url="http://test.com/success",
            cancel_url="http://test.com/cancel",
            metadata={"description": "Test payment"},
            email="test@example.com"
        )
        
        assert result.success is True
        assert result.reference == "REF123"
        assert "paystack.com" in result.redirect_url
    
    @responses.activate
    def test_initialize_payment_missing_email(self, settings):
        """Test that email is required for Paystack"""
        settings.PAYSTACK_SECRET_KEY = "test_secret_key"
        
        gateway = PaystackGateway()
        result = gateway.initialize_payment(
            amount=Decimal("100.00"),
            currency="USD",
            return_url="http://test.com/success",
            cancel_url="http://test.com/cancel",
            metadata={},
            email=None  # Missing email
        )
        
        assert result.success is False
        assert "email" in result.error.lower()
\`\`\`

---

## 5. Deployment & Maintenance Best Practices

### 5.1 Adding a New Payment Gateway

Thanks to the Open/Closed principle, adding a new gateway (e.g., Stripe) requires:

1. **Create gateway class** implementing `PaymentGatewayInterface`:

\`\`\`python
# apps/payments/gateways/stripe.py
from .base import PaymentGatewayInterface, PaymentInitResult, ...

class StripeGateway(PaymentGatewayInterface):
    @property
    def gateway_name(self) -> str:
        return "stripe"
    
    def initialize_payment(self, ...) -> PaymentInitResult:
        # Stripe-specific implementation
        pass
    
    # ... implement other methods
\`\`\`

2. **Register the gateway**:

\`\`\`python
# apps/payments/apps.py
from django.apps import AppConfig

class PaymentsConfig(AppConfig):
    name = 'apps.payments'
    
    def ready(self):
        from .services import PaymentService
        from .gateways.stripe import StripeGateway
        
        PaymentService.register_gateway('stripe', StripeGateway())
\`\`\`

3. **No changes needed** to `PaymentService` or views!

### 5.2 Environment Configuration

\`\`\`python
# shadowiq/settings/base.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Local apps
    'apps.users',
    'apps.projects',
    'apps.payments',
    'apps.messaging',
    'apps.audit',
    'apps.negotiations',
    'common',
]

# Custom user model
AUTH_USER_MODEL = 'users.PseudonymousUser'
\`\`\`

### 5.3 Migration Strategy

1. **Phase 1**: Create new app structure alongside `core`
2. **Phase 2**: Move models one domain at a time with Django migrations
3. **Phase 3**: Refactor views to use new services
4. **Phase 4**: Update URLs to point to new app views
5. **Phase 5**: Remove `core` app after all migrations complete

---

## 6. Summary: How Each Change Improves the System

| Change | SOLID Principle | Benefit |
|--------|-----------------|---------|
| Lean models (fields only) | Single Responsibility | Models don't change when business rules change |
| Service classes | Single Responsibility | Business logic centralized and reusable |
| Selector classes | Single Responsibility | Query logic separate from business logic |
| Gateway interface | Open/Closed, Dependency Inversion | New gateways without modifying existing code |
| PaymentService orchestrator | Interface Segregation | Views don't depend on gateway details |
| Thin views | Single Responsibility | HTTP concerns separate from business logic |
| Modular apps | High Cohesion | Related code grouped together |
| Dataclass results | Explicit contracts | Clear input/output types for testing |

### Testability Improvements

| Layer | Testability |
|-------|-------------|
| **Services** | Unit test with mocked dependencies |
| **Selectors** | Integration test with test DB |
| **Gateways** | Unit test with mocked HTTP |
| **Views** | Integration test with Django test client |
| **Models** | Simple property tests |

This architecture allows you to:
- Test business logic without Django
- Mock payment gateways without network calls
- Add new features without modifying existing code
- Maintain clear boundaries between domains
