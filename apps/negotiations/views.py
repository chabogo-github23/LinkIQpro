"""
Negotiations Domain Views
"""
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from apps.projects.models import Project
from apps.users.decorators import pseudonymous_user_required as require_auth
from apps.audit.services import AuditService
from apps.messaging.services import ChatService
from .services import NegotiationService
from .models import ProjectNegotiation


@require_auth
def propose_price(request, project_id):
    """Propose a price for the project"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if not (project.client == request.user or request.user.is_admin):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            proposed_price = float(request.POST.get('price', 0))
            proposed_deadline = request.POST.get('deadline')
            
            success, message = NegotiationService.propose_price(
                project, request.user, proposed_price, proposed_deadline
            )
            
            if not success:
                return JsonResponse({'error': message}, status=400)
            
            # Create proposal message
            from apps.messaging.models import Message
            Message.objects.create(
                project=project,
                sender=request.user,
                message_type='proposal',
                content=f"Proposed price: ${proposed_price}",
                metadata={
                    'price': str(proposed_price),
                    'deadline': proposed_deadline,
                    'proposer': 'admin' if request.user.is_admin else 'client'
                }
            )
            
            AuditService.log_from_request('price_proposed', request, project,
                details={'price': proposed_price})
            
            return JsonResponse({'success': True, 'message': message})
            
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid price format'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@require_auth
def agree_terms(request, project_id):
    """Client agrees to proposed terms"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if not (project.client == request.user or request.user.is_admin):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        success, message = NegotiationService.agree_terms(project, request.user)
        
        if not success:
            return JsonResponse({'error': message}, status=400)
        
        # Get agreed price for message
        try:
            negotiation = ProjectNegotiation.objects.get(project=project)
            
            from apps.messaging.models import Message
            Message.objects.create(
                project=project,
                sender=request.user,
                message_type='agreement',
                content=f"Client agreed to terms: ${negotiation.agreed_price}",
                metadata={'price': str(negotiation.agreed_price)}
            )
            
            AuditService.log_from_request('terms_agreed', request, project,
                details={'price': str(negotiation.agreed_price)})
        except ProjectNegotiation.DoesNotExist:
            pass
        
        return JsonResponse({'success': True, 'message': message})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
