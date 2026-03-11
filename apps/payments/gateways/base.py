"""
Payment Gateway Abstract Base
Interface Segregation: Define clear contract for payment gateways
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from decimal import Decimal


@dataclass
class PaymentInitResult:
    success: bool
    authorization_url: Optional[str] = None
    reference: Optional[str] = None
    order_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PaymentVerifyResult:
    success: bool
    is_successful: bool = False
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    reference: Optional[str] = None
    status: Optional[str] = None
    gateway_response: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PaymentCaptureResult:
    success: bool
    capture_id: Optional[str] = None
    amount: Optional[Decimal] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentGatewayInterface(ABC):
    """
    Abstract interface for payment gateways
    Dependency Inversion: High-level modules depend on this abstraction
    """
    
    @abstractmethod
    def initialize_payment(self, email: str, amount: Decimal, 
                          callback_url: str, metadata: Dict[str, Any] = None,
                          currency: str = 'USD') -> PaymentInitResult:
        """Initialize a payment and return authorization URL"""
        pass
    
    @abstractmethod
    def verify_payment(self, reference: str) -> PaymentVerifyResult:
        """Verify a payment by reference"""
        pass
    
    @abstractmethod
    def get_gateway_name(self) -> str:
        """Return the gateway identifier"""
        pass


class EscrowCapableGateway(PaymentGatewayInterface):
    """
    Extended interface for gateways supporting escrow/authorization
    Interface Segregation: Separate escrow capability
    """
    
    @abstractmethod
    def authorize_payment(self, order_id: str) -> PaymentVerifyResult:
        """Authorize (hold) payment without capturing"""
        pass
    
    @abstractmethod
    def capture_payment(self, auth_id: str, amount: Decimal = None) -> PaymentCaptureResult:
        """Capture an authorized payment"""
        pass
    
    @abstractmethod
    def void_authorization(self, auth_id: str) -> bool:
        """Void an authorization (release held funds back to customer)"""
        pass
