"""
Payments Domain Services
Business logic for payment operations following SOLID principles
"""
from typing import Optional, List, Tuple
from dataclasses import dataclass
from decimal import Decimal
from django.utils import timezone
import logging

from apps.projects.models import Project, Milestone
from apps.projects.repositories import MilestoneRepository
from .gateways.factory import PaymentGatewayFactory
from .gateways.base import PaymentInitResult, PaymentVerifyResult, PaymentCaptureResult
from .utils import convert_usd_to_currency, format_currency_amount

logger = logging.getLogger(__name__)


@dataclass
class PaymentProcessResult:
    success: bool
    authorization_url: Optional[str] = None
    reference: Optional[str] = None
    order_id: Optional[str] = None
    error: Optional[str] = None
    milestone_count: int = 0
    total_amount: Decimal = Decimal('0')
    converted_amount: Optional[float] = None
    currency: str = 'USD'


class MilestonePaymentService:
    """
    Service for milestone payment processing
    Single Responsibility: Coordinate payment operations
    """
    
    def __init__(self, milestone_repo: MilestoneRepository = None):
        self.milestone_repo = milestone_repo or MilestoneRepository()
    
    def initiate_payment(self, project: Project, milestone_ids: List[str],
                        gateway_name: str, callback_url: str,
                        user_email: str = None, currency: str = 'USD') -> PaymentProcessResult:
        """Initiate payment for milestones"""
        
        # Get gateway
        gateway = PaymentGatewayFactory.create(gateway_name)
        if not gateway:
            return PaymentProcessResult(success=False, error='Invalid payment gateway')
        
        # Get payable milestones
        if milestone_ids:
            milestones = list(project.milestones.filter(
                id__in=milestone_ids,
                payment_status__in=['unfunded', 'processing']
            ))
        else:
            milestones = self.milestone_repo.get_unfunded_milestones(project)
        
        if not milestones:
            return PaymentProcessResult(success=False, error='No milestones to pay for')
        
        total_amount = sum(m.amount for m in milestones)
        
        # Gateway-specific handling
        if gateway_name == 'paystack':
            if not user_email:
                return PaymentProcessResult(
                    success=False, 
                    error='Email required for Paystack payment'
                )
            return self._process_paystack_init(
                gateway, project, milestones, total_amount, 
                callback_url, user_email, currency
            )
        else:
            return self._process_paypal_init(
                gateway, project, milestones, total_amount, callback_url
            )
    
    def _process_paypal_init(self, gateway, project: Project, milestones: List[Milestone],
                            total_amount: Decimal, callback_url: str) -> PaymentProcessResult:
        """Process PayPal payment initialization"""
        try:
            # Reset any processing milestones
            for milestone in milestones:
                if milestone.payment_status == 'processing':
                    milestone.payment_status = 'unfunded'
                    milestone.gateway_used = None
                    milestone.paypal_order_id = None
                    milestone.paypal_auth_id = None
                    milestone.save()
            
            result = gateway.initialize_payment(
                email='',
                amount=total_amount,
                callback_url=callback_url,
                metadata={
                    'project_id': str(project.project_id),
                    'description': f'Payment for {len(milestones)} milestones'
                }
            )
            
            if result.success:
                # Update milestones
                first_milestone = milestones[0]
                first_milestone.paypal_order_id = result.order_id
                first_milestone.payment_status = 'processing'
                first_milestone.gateway_used = 'paypal'
                first_milestone.save()
                
                for milestone in milestones[1:]:
                    milestone.payment_status = 'processing'
                    milestone.gateway_used = 'paypal'
                    milestone.save()
                
                return PaymentProcessResult(
                    success=True,
                    authorization_url=result.authorization_url,
                    order_id=result.order_id,
                    milestone_count=len(milestones),
                    total_amount=total_amount,
                    currency='USD'
                )
            
            return PaymentProcessResult(success=False, error=result.error)
            
        except Exception as e:
            logger.error(f"PayPal init error: {e}")
            # Reset milestones on error
            for milestone in milestones:
                milestone.payment_status = 'unfunded'
                milestone.gateway_used = None
                milestone.paypal_order_id = None
                milestone.save()
            return PaymentProcessResult(success=False, error=str(e))
    
    def _process_paystack_init(self, gateway, project: Project, milestones: List[Milestone],
                              total_amount: Decimal, callback_url: str,
                              user_email: str, currency: str) -> PaymentProcessResult:
        """
        Process Paystack payment initialization.
        The gateway handles USD to target currency conversion automatically.
        """
        try:
            logger.info(
                f"Initiating Paystack payment: project={project.project_id}, "
                f"amount=${total_amount} USD, target_currency={currency}, "
                f"milestones={len(milestones)}"
            )
            
            # Gateway handles USD -> target currency conversion internally
            result = gateway.initialize_payment(
                email=user_email,
                amount=total_amount,  # USD amount - gateway will convert
                callback_url=callback_url,
                metadata={
                    'project_id': str(project.project_id),
                    'milestone_ids': [str(m.id) for m in milestones],
                    'payment_type': 'milestone_batch',
                    'original_amount_usd': float(total_amount)
                },
                currency=currency
            )
            
            if result.success:
                # Get converted amount from result metadata if available
                converted_amount = None
                if result.metadata:
                    converted_amount = result.metadata.get('converted_amount')
                
                # Update milestones with payment info
                for milestone in milestones:
                    milestone.payment_status = 'processing'
                    milestone.gateway_used = 'paystack'
                    milestone.paystack_reference = result.reference
                    milestone.paystack_currency = currency
                    milestone.save()
                
                logger.info(
                    f"Paystack payment initiated: ref={result.reference}, "
                    f"converted={converted_amount} {currency}"
                )
                
                return PaymentProcessResult(
                    success=True,
                    authorization_url=result.authorization_url,
                    reference=result.reference,
                    milestone_count=len(milestones),
                    total_amount=total_amount,
                    converted_amount=converted_amount,
                    currency=currency
                )
            
            return PaymentProcessResult(success=False, error=result.error)
            
        except Exception as e:
            logger.error(f"Paystack init error: {e}")
            # Reset milestones on error
            for milestone in milestones:
                milestone.payment_status = 'unfunded'
                milestone.gateway_used = None
                milestone.paystack_reference = None
                milestone.paystack_currency = None
                milestone.save()
            return PaymentProcessResult(success=False, error=str(e))
    
    def verify_paystack_payment(self, project: Project, reference: str) -> Tuple[bool, str, List[Milestone]]:
        """Verify Paystack payment and update milestones"""
        gateway = PaymentGatewayFactory.create('paystack')
        result = gateway.verify_payment(reference)
        
        milestones = list(project.milestones.filter(
            paystack_reference=reference,
            payment_status='processing'
        ))
        
        if result.success and result.is_successful:
            for milestone in milestones:
                milestone.payment_status = 'funded'
                milestone.funded_at = timezone.now()
                milestone.save()
            
            return True, 'Payment successful', milestones
        
        # Payment failed - reset milestones
        for milestone in milestones:
            milestone.payment_status = 'unfunded'
            milestone.gateway_used = None
            milestone.paystack_reference = None
            milestone.paystack_currency = None
            milestone.save()
        
        error = result.error or result.gateway_response or 'Verification failed'
        return False, error, milestones
    
    def verify_paypal_payment(self, project: Project, order_id: str) -> Tuple[bool, str, List[Milestone], Optional[str]]:
        """Verify and authorize PayPal payment"""
        gateway = PaymentGatewayFactory.get_escrow_gateway('paypal')
        
        milestones = list(project.milestones.filter(
            payment_status='processing',
            gateway_used='paypal'
        ))
        
        try:
            result = gateway.authorize_payment(order_id)
            
            if result.success:
                auth_id = result.reference
                
                # Update milestones
                if milestones:
                    first_milestone = milestones[0]
                    first_milestone.paypal_auth_id = auth_id
                    first_milestone.payment_status = 'funded'
                    first_milestone.funded_at = timezone.now()
                    first_milestone.save()
                    
                    for milestone in milestones[1:]:
                        milestone.payment_status = 'funded'
                        milestone.funded_at = timezone.now()
                        milestone.save()
                
                return True, 'Funds held in escrow', milestones, auth_id
            
            raise Exception(result.error or 'Authorization failed')
            
        except Exception as e:
            # Reset milestones on error
            for milestone in milestones:
                milestone.payment_status = 'unfunded'
                milestone.gateway_used = None
                milestone.paypal_order_id = None
                milestone.paypal_auth_id = None
                milestone.save()
            
            return False, str(e), milestones, None
    
    def release_paypal_payment(self, milestone: Milestone) -> Tuple[bool, str]:
        """Capture/release PayPal payment"""
        if not milestone.is_releasable:
            return False, 'Milestone not ready for release'
        
        if milestone.gateway_used != 'paypal' or not milestone.paypal_auth_id:
            return False, 'Not a PayPal payment or missing authorization'
        
        gateway = PaymentGatewayFactory.get_escrow_gateway('paypal')
        result = gateway.capture_payment(milestone.paypal_auth_id, milestone.amount)
        
        if result.success:
            milestone.payment_status = 'released'
            milestone.released_at = timezone.now()
            milestone.save()
            return True, f'Payment released for {milestone.title}'
        
        return False, result.error or 'Capture failed'
    
    def cancel_payment(self, project: Project) -> int:
        """Cancel all processing payments and reset milestones"""
        processing_milestones = project.milestones.filter(payment_status='processing')
        count = processing_milestones.count()
        
        processing_milestones.update(
            payment_status='unfunded',
            gateway_used=None,
            paypal_order_id=None,
            paypal_auth_id=None,
            paystack_reference=None,
            paystack_currency=None
        )
        
        return count
