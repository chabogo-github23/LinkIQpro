"""
PayPal Payment Gateway Implementation
Open/Closed: Extends gateway interface without modifying it
"""
import requests
import base64
from decimal import Decimal
from typing import Dict, Any, Optional
from django.conf import settings

from .base import (
    EscrowCapableGateway, 
    PaymentInitResult, 
    PaymentVerifyResult,
    PaymentCaptureResult
)


class PayPalGateway(EscrowCapableGateway):
    """PayPal payment gateway with escrow support"""
    
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.base_url = getattr(settings, 'PAYPAL_BASE_URL', 'https://api-m.sandbox.paypal.com')
        self._access_token = None
    
    def get_gateway_name(self) -> str:
        return 'paypal'
    
    def _get_access_token(self) -> str:
        """Get OAuth2 access token from PayPal"""
        if self._access_token:
            return self._access_token
        
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        
        response = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {auth_bytes}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={"grant_type": "client_credentials"},
            timeout=30
        )
        
        if response.status_code == 200:
            self._access_token = response.json().get("access_token")
            return self._access_token
        
        raise Exception(f"Failed to get PayPal access token: {response.text}")
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json"
        }
    
    def initialize_payment(self, email: str, amount: Decimal, 
                          callback_url: str, metadata: Dict[str, Any] = None,
                          currency: str = 'USD') -> PaymentInitResult:
        """Create PayPal order with authorization intent"""
        try:
            # Parse callback URLs
            return_url = callback_url
            cancel_url = callback_url.replace('/success/', '/cancel/')
            
            order_data = {
                "intent": "AUTHORIZE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": currency,
                        "value": str(amount)
                    },
                    "description": metadata.get('description', 'Milestone Payment') if metadata else 'Milestone Payment'
                }],
                "application_context": {
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                    "brand_name": "ShadowIQ",
                    "user_action": "PAY_NOW"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders",
                headers=self._get_headers(),
                json=order_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                order_id = data.get("id")
                
                # Find approval URL
                approval_url = None
                for link in data.get("links", []):
                    if link.get("rel") == "approve":
                        approval_url = link.get("href")
                        break
                
                return PaymentInitResult(
                    success=True,
                    order_id=order_id,
                    authorization_url=approval_url,
                    reference=order_id
                )
            
            return PaymentInitResult(
                success=False,
                error=f"PayPal order creation failed: {response.text}"
            )
            
        except Exception as e:
            return PaymentInitResult(success=False, error=str(e))
    
    def verify_payment(self, reference: str) -> PaymentVerifyResult:
        """Get order details"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/checkout/orders/{reference}",
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                return PaymentVerifyResult(
                    success=True,
                    is_successful=status in ["APPROVED", "COMPLETED"],
                    status=status,
                    reference=reference,
                    metadata=data
                )
            
            return PaymentVerifyResult(
                success=False,
                error=f"Failed to verify PayPal order: {response.text}"
            )
            
        except Exception as e:
            return PaymentVerifyResult(success=False, error=str(e))
    
    def authorize_payment(self, order_id: str) -> PaymentVerifyResult:
        """Authorize (hold) the payment"""
        try:
            response = requests.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/authorize",
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                # Extract authorization ID
                auth_id = None
                try:
                    auth_id = data["purchase_units"][0]["payments"]["authorizations"][0]["id"]
                except (KeyError, IndexError):
                    pass
                
                return PaymentVerifyResult(
                    success=True,
                    is_successful=True,
                    reference=auth_id,
                    status="AUTHORIZED",
                    metadata=data
                )
            
            return PaymentVerifyResult(
                success=False,
                error=f"PayPal authorization failed: {response.text}"
            )
            
        except Exception as e:
            return PaymentVerifyResult(success=False, error=str(e))
    
    def capture_payment(self, auth_id: str, amount: Decimal = None) -> PaymentCaptureResult:
        """Capture an authorized payment"""
        try:
            capture_data = {}
            if amount:
                capture_data["amount"] = {
                    "currency_code": "USD",
                    "value": str(amount)
                }
            
            response = requests.post(
                f"{self.base_url}/v2/payments/authorizations/{auth_id}/capture",
                headers=self._get_headers(),
                json=capture_data if capture_data else None,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return PaymentCaptureResult(
                    success=True,
                    capture_id=data.get("id"),
                    amount=Decimal(data.get("amount", {}).get("value", "0")),
                    metadata=data
                )
            
            return PaymentCaptureResult(
                success=False,
                error=f"PayPal capture failed: {response.text}"
            )
            
        except Exception as e:
            return PaymentCaptureResult(success=False, error=str(e))
    
    def void_authorization(self, auth_id: str) -> bool:
        """Void an authorization"""
        try:
            response = requests.post(
                f"{self.base_url}/v2/payments/authorizations/{auth_id}/void",
                headers=self._get_headers(),
                timeout=30
            )
            return response.status_code in [200, 204]
        except:
            return False
