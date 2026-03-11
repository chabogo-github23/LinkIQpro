"""
Payment Gateway Factory
Factory Pattern: Create gateway instances based on type
"""
from typing import Optional
from .base import PaymentGatewayInterface, EscrowCapableGateway
from .paypal import PayPalGateway
from .paystack import PaystackGateway


class PaymentGatewayFactory:
    """Factory for creating payment gateway instances"""
    
    _gateways = {
        'paypal': PayPalGateway,
        'paystack': PaystackGateway,
    }
    
    @classmethod
    def create(cls, gateway_name: str) -> Optional[PaymentGatewayInterface]:
        """Create a gateway instance by name"""
        gateway_class = cls._gateways.get(gateway_name.lower())
        if gateway_class:
            return gateway_class()
        return None
    
    @classmethod
    def get_escrow_gateway(cls, gateway_name: str) -> Optional[EscrowCapableGateway]:
        """Get an escrow-capable gateway"""
        gateway = cls.create(gateway_name)
        if isinstance(gateway, EscrowCapableGateway):
            return gateway
        return None
    
    @classmethod
    def get_available_gateways(cls) -> list:
        """List available gateway names"""
        return list(cls._gateways.keys())
