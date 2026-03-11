"""
Core Views Module - Backward Compatibility Layer
Re-exports views from domain apps for existing URL patterns
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.views.generic import TemplateView

# Re-export User views
from apps.users.views import (
    home,
    register,
    request_magic_link,
    verify_magic_link,
    logout_view,
    password_reset_request,
    password_reset_confirm,
    client_dashboard,
    analyst_dashboard,
    admin_dashboard,
    admin_user_management,
    admin_user_detail,
    admin_create_user,
    admin_edit_user,
    admin_delete_user,
)

# Re-export Project views
from apps.projects.views import (
    project_detail,
    submit_project,
    analyst_project_detail,
    analyst_upload_deliverable,
    analyst_submit_work,
    create_milestone,
    update_milestone_status,
    approve_milestone,
    project_triage,
    admin_upload_progress,
    admin_project_review,
    admin_assign_analyst,
    admin_review_deliverable,
)

# Re-export Payment views
from apps.payments.views import (
    milestone_payment_page,
    create_milestone_payment,
    validate_payment_email,
    payment_success,
    payment_cancel,
    release_milestone_payment,
)

# Re-export Messaging views
from apps.messaging.views import (
    project_chat,
)

# Re-export Negotiation views
from apps.negotiations.views import (
    propose_price,
    agree_terms,
)

# Re-export decorators for backward compatibility
from apps.users.decorators import (
    pseudonymous_user_required as require_auth,
    admin_required as require_admin,
    analyst_required as require_analyst,
    client_required,
    get_client_ip,
)


# Alias for backward compatibility with URL imports
request_password_reset = password_reset_request


# Additional views that weren't in domain apps
def login_placeholder(request):
    """Temporary login page placeholder"""
    return render(request, 'core/login.html')


def view_progress_pdf(request, progress_id):
    """View a project progress PDF file"""
    from apps.projects.models import ProjectProgress
    
    progress = get_object_or_404(ProjectProgress, id=progress_id)
    return render(request, 'core/view_progress_pdf.html', {'progress': progress})


def analyst_view_messages(request, project_id):
    """Analyst views project messages - redirect to chat"""
    from apps.projects.models import Project
    project = get_object_or_404(Project, project_id=project_id)
    return project_chat(request, project_id)


def admin_deliver_to_client(request, project_id):
    """Admin delivers completed project to client"""
    from django.utils import timezone
    from datetime import timedelta
    from django.http import JsonResponse
    import secrets
    
    from apps.projects.models import Project
    from apps.messaging.services import ChatService
    from apps.audit.services import AuditService
    
    project = get_object_or_404(Project, project_id=project_id)
    
    if project.status != 'completed':
        return JsonResponse({'error': 'Project must be completed first'}, status=400)
    
    if request.method == 'POST':
        # Create download tokens for deliverables
        from .models import DownloadToken
        
        for deliverable in project.deliverables.all():
            token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(days=30)
            
            DownloadToken.objects.create(
                deliverable=deliverable,
                token=token,
                expires_at=expires_at
            )
        
        ChatService().create_system_message(project, 'Project delivered to client. Download links sent.')
        AuditService.log_from_request('project_delivered', request, project)
        
        return JsonResponse({'success': True, 'message': 'Project delivered to client'})
    
    
