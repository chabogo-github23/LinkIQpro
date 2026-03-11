"""
Paystack Payment Gateway Implementation
Open/Closed: Extends gateway interface without modifying it
"""
import requests
from decimal import Decimal
from typing import Dict, Any
from django.conf import settings
from django.utils import timezone
import logging

from .base import PaymentGatewayInterface, PaymentInitResult, PaymentVerifyResult
from apps.payments.utils import convert_usd_to_currency, SUPPORTED_CURRENCIES

logger = logging.getLogger(__name__)


class PaystackGateway(PaymentGatewayInterface):
    """Paystack payment gateway (direct charge, no escrow)"""
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = 'https://api.paystack.co'
    
    def get_gateway_name(self) -> str:
        return 'paystack'
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def initialize_payment(self, email: str, amount: Decimal, 
                          callback_url: str, metadata: Dict[str, Any] = None,
                          currency: str = 'USD') -> PaymentInitResult:
        """
        Initialize Paystack payment with automatic USD to target currency conversion.
        
        Args:
            email: Customer email
            amount: Amount in USD (will be converted to target currency)
            callback_url: URL to redirect after payment
            metadata: Additional payment metadata
            currency: Target currency (KES, NGN, GHS, etc.)
        
        Returns:
            PaymentInitResult with authorization URL or error
        """
        try:
            amount_usd = float(amount)
            amount_in_smallest, converted_amount, error = convert_usd_to_currency(amount_usd, currency)
            
            if error:
                logger.error(f"Currency conversion failed: {error}")
                return PaymentInitResult(success=False, error=error)
            
            logger.info(
                f"Paystack payment: ${amount_usd} USD -> {converted_amount:.2f} {currency} "
                f"(smallest unit: {amount_in_smallest})"
            )
            
            # Add conversion info to metadata for transparency
            enhanced_metadata = metadata or {}
            enhanced_metadata.update({
                'original_amount_usd': amount_usd,
                'converted_amount': converted_amount,
                'target_currency': currency,
            })
            
            payload = {
                "email": email,
                "amount": amount_in_smallest,  # Already in smallest currency unit
                "callback_url": callback_url,
                "currency": currency,
                "metadata": enhanced_metadata
            }
            
            logger.info(f"Paystack payload: email={email}, amount={amount_in_smallest}, currency={currency}")
            
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            data = response.json()
            
            if data.get("status"):
                return PaymentInitResult(
                    success=True,
                    authorization_url=data["data"]["authorization_url"],
                    reference=data["data"]["reference"],
                    # Store conversion info for reference
                    metadata={
                        'converted_amount': converted_amount,
                        'currency': currency,
                        'original_usd': amount_usd
                    }
                )
            
            error_msg = data.get("message", "Payment initialization failed")
            logger.error(f"Paystack init failed: {error_msg}")
            return PaymentInitResult(success=False, error=error_msg)
            
        except requests.RequestException as e:
            logger.error(f"Paystack request error: {e}")
            return PaymentInitResult(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Paystack initialization error: {e}")
            return PaymentInitResult(success=False, error=str(e))
    
    def verify_payment(self, reference: str) -> PaymentVerifyResult:
        """Verify Paystack payment"""
        try:
            response = requests.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self._get_headers(),
                timeout=30
            )
            
            data = response.json()
            
            if data.get("status"):
                tx_data = data.get("data", {})
                tx_status = tx_data.get("status")
                
                # Get the amount in major units
                amount_minor = tx_data.get("amount", 0)
                currency = tx_data.get("currency", "USD")
                amount_major = Decimal(amount_minor) / 100
                
                return PaymentVerifyResult(
                    success=True,
                    is_successful=(tx_status == "success"),
                    amount=amount_major,
                    currency=currency,
                    reference=reference,
                    status=tx_status,
                    gateway_response=tx_data.get("gateway_response"),
                    metadata=tx_data
                )
            
            return PaymentVerifyResult(
                success=False,
                error=data.get("message", "Verification failed")
            )
            
        except Exception as e:
            logger.error(f"Paystack verification error: {e}")
            return PaymentVerifyResult(success=False, error=str(e))


def create_milestone_metadata(project, milestones, payment_type="individual"):
    """Create metadata for milestone payments"""
    
    milestone_ids = []
    milestone_titles = []
    total_amount = 0
    
    for milestone in milestones:
        if hasattr(milestone, 'id'):
            milestone_ids.append(str(milestone.id))
            milestone_titles.append(milestone.title)
            total_amount += float(milestone.amount)
        else:
            milestone_ids.append(str(milestone))
    
    return {
        "project_id": str(project.project_id),
        "project_title": project.title,
        "milestone_ids": milestone_ids,
        "milestone_titles": milestone_titles,
        "payment_type": payment_type,
        "total_amount": total_amount,
        "milestone_count": len(milestone_ids),
        "timestamp": timezone.now().isoformat()
    }


def validate_currency_support(currency):
    """Validate if currency is supported"""
    if currency not in SUPPORTED_CURRENCIES:
        return False, f"Currency {currency} not supported. Supported: {', '.join(SUPPORTED_CURRENCIES)}"
    
    return True, None


def calculate_milestone_totals(milestones):
    """Calculate totals for milestones"""
    total = sum(milestone.amount for milestone in milestones)
    breakdown = [
        {
            'id': str(milestone.id),
            'title': milestone.title,
            'amount': float(milestone.amount),
            'due_date': milestone.due_date.isoformat() if milestone.due_date else None
        }
        for milestone in milestones
    ]
    
    return {
        'total_amount': float(total),
        'milestone_count': len(milestones),
        'breakdown': breakdown
    }
