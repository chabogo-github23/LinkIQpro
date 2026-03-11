"""
Negotiations Domain Services
"""
from typing import Optional, Tuple
from decimal import Decimal
from django.utils import timezone
from .models import ProjectNegotiation
from apps.projects.models import Project
from apps.users.models import PseudonymousUser


class NegotiationService:
    """Service for project negotiations"""
    
    @staticmethod
    def get_or_create_negotiation(project: Project) -> ProjectNegotiation:
        """Get or create a negotiation for a project"""
        negotiation, _ = ProjectNegotiation.objects.get_or_create(
            project=project,
            defaults={'status': 'pending'}
        )
        return negotiation
    
    @staticmethod
    def propose_price(project: Project, proposer: PseudonymousUser,
                     price: Decimal, deadline=None) -> Tuple[bool, str]:
        """Propose a price for the project"""
        if price <= 0:
            return False, 'Invalid price'
        
        negotiation = NegotiationService.get_or_create_negotiation(project)
        negotiation.proposed_price = price
        if deadline:
            negotiation.proposed_deadline = deadline
        negotiation.status = 'in_progress'
        negotiation.save()
        
        return True, 'Price proposal sent'
    
    @staticmethod
    def agree_terms(project: Project, user: PseudonymousUser) -> Tuple[bool, str]:
        """Client agrees to proposed terms"""
        try:
            negotiation = ProjectNegotiation.objects.get(project=project)
        except ProjectNegotiation.DoesNotExist:
            return False, 'No active negotiation'
        
        if user != project.client:
            return False, 'Only client can finalize agreement'
        
        negotiation.agreed_price = negotiation.proposed_price
        negotiation.agreed_deadline = negotiation.proposed_deadline
        negotiation.status = 'agreed'
        negotiation.agreed_at = timezone.now()
        negotiation.save()
        
        # Update project
        project.total_price = negotiation.agreed_price
        project.deadline = negotiation.agreed_deadline
        project.status = 'accepted'
        project.save()
        
        return True, 'Terms agreed. Ready for payment.'
