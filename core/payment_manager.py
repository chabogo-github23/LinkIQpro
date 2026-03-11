"""
Core Payment Manager - Backward Compatibility Layer
Re-exports payment functionality from apps.payments.gateways
"""

# Re-export from new gateway abstraction for backward compatibility
from apps.payments.gateways.paypal import PayPalGateway
from apps.payments.gateways.factory import PaymentGatewayFactory

# Import settings for backward compatibility
from django.conf import settings

PAYPAL_API_BASE = getattr(settings, 'PAYPAL_BASE_URL', 'https://api-m.sandbox.paypal.com')


class PayPalManager:
    """
    Backward compatibility wrapper for PayPal operations.
    Delegates to the new PayPalGateway class.
    """
    
    @staticmethod
    def get_access_token():
        """Get OAuth2 access token"""
        gateway = PayPalGateway()
        return gateway._get_access_token()
    
    @staticmethod
    def create_milestone_order(project, milestones, total_amount, request):
        """Create PayPal order for milestones"""
        gateway = PayPalGateway()
        
        callback_url = request.build_absolute_uri(
            f"/project/{project.project_id}/payment/success/?method=paypal"
        )
        
        result = gateway.initialize_payment(
            email='',
            amount=total_amount,
            callback_url=callback_url,
            metadata={
                'project_id': str(project.project_id),
                'milestone_ids': [str(m.id) for m in milestones],
                'description': f'Payment for {len(milestones)} milestones'
            }
        )
        
        if result.success:
            return result.order_id, result.authorization_url
        raise Exception(result.error)
    
    @staticmethod
    def authorize_milestone_order(project, order_id):
        """Authorize PayPal order after approval"""
        gateway = PayPalGateway()
        result = gateway.authorize_payment(order_id)
        
        if result.success:
            return True, result.metadata
        return False, result.error
    
    @staticmethod
    def capture_milestone_payment(milestone):
        """Capture authorized payment"""
        if not milestone.paypal_auth_id:
            return False, "Missing Authorization ID"
        
        gateway = PayPalGateway()
        result = gateway.capture_payment(milestone.paypal_auth_id, milestone.amount)
        
        if result.success:
            return True, result.metadata
        return False, result.error
    
    @staticmethod
    def get_authorization_details(authorization_id):
        """Get authorization details"""
        import requests
        
        gateway = PayPalGateway()
        try:
            response = requests.get(
                f"{PAYPAL_API_BASE}/v2/payments/authorizations/{authorization_id}",
                headers=gateway._get_headers(),
                timeout=30
            )
            if response.status_code == 200:
                return True, response.json()
            return False, response.json().get('message', 'Failed')
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def void_milestone_authorization(milestone):
        """Void an authorization"""
        if not milestone.paypal_auth_id:
            return False, "Missing Authorization ID"
        
        gateway = PayPalGateway()
        success = gateway.void_authorization(milestone.paypal_auth_id)
        return success, "Voided" if success else "Void failed"
    
    @staticmethod
    def refund_milestone_payment(milestone, amount=None):
        """Refund a captured payment"""
        # This would need the capture ID, which requires more complex logic
        return False, "Refund not implemented in compatibility layer"
    
    @staticmethod
    def release_multiple_milestones(milestones):
        """Release payments for multiple milestones"""
        results = []
        for milestone in milestones:
            success, data = PayPalManager.capture_milestone_payment(milestone)
            results.append({
                'milestone_id': str(milestone.id),
                'title': milestone.title,
                'success': success,
                'data': data,
                'amount': float(milestone.amount)
            })
        return results


# Helper functions for backward compatibility
def validate_milestones_for_payment(milestones):
    """Validate milestones for payment"""
    errors = []
    if not milestones:
        return ["No milestones provided"]
    
    for milestone in milestones:
        if milestone.payment_status not in ['unfunded', 'processing']:
            errors.append(f"Milestone '{milestone.title}' is already funded")
        if milestone.amount <= 0:
            errors.append(f"Milestone '{milestone.title}' has invalid amount")
    
    return errors


def calculate_milestone_totals(milestones):
    """Calculate totals for milestones"""
    if not milestones:
        return {
            'total_amount': 0.0,
            'milestone_count': 0,
            'breakdown': [],
            'is_valid': False,
            'errors': ['No milestones provided']
        }
    
    total = sum(m.amount for m in milestones)
    breakdown = [{
        'title': m.title,
        'amount': float(m.amount),
        'due_date': m.due_date.isoformat() if m.due_date else None,
        'status': m.payment_status
    } for m in milestones]
    
    return {
        'total_amount': float(total),
        'milestone_count': len(milestones),
        'breakdown': breakdown,
        'is_valid': True,
        'errors': []
    }
