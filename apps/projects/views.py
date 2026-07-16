"""
Projects Domain Views
Thin controllers that delegate to services
"""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.urls import reverse

from .models import Project, Milestone, ProjectFile, ProjectProgress
from .services import (
    ProjectSubmissionService,
    ProjectWorkflowService,
    MilestoneService,
    DeliverableService,
    ProjectActivityService
)
from .repositories import ProjectRepository, MilestoneRepository
from apps.users.decorators import (
    pseudonymous_user_required as require_auth,
    admin_required as require_admin,
    analyst_required as require_analyst,
    client_required,
    sub_admin_required
)
from apps.users.models import PseudonymousUser
from apps.audit.services import AuditService
from apps.messaging.services import ChatService


@require_auth
def project_detail(request, project_id):
    """View project details"""
    project = get_object_or_404(Project, project_id=project_id)

    if request.user.is_sub_admin:
        if project.tenant_admin_id != request.user.id:
            return render(request, 'core/access_denied.html', status=403)
    elif project.client.id != request.user.id and not request.user.is_admin:
        return render(request, 'core/access_denied.html', status=403)
    
    from apps.users.repositories import UserRepository
    admins = UserRepository.get_admins()
    progress_updates = ProjectProgress.objects.filter(project=project).order_by('-uploaded_at')
    
    milestones = project.milestones.all()
    total_count = milestones.count()
    funded_count = milestones.filter(payment_status__in=['funded', 'released']).count()
    released_count = milestones.filter(payment_status='released').count()
    has_unfunded_milestones = milestones.filter(payment_status='unfunded').exists()
    has_processing_milestones = milestones.filter(payment_status='processing').exists()
    processing_count = milestones.filter(payment_status='processing').count()
    activity_service = ProjectActivityService()
    project_activities = activity_service.get_project_activities(project, request.user, limit=40)
    activity_unread_count = activity_service.get_unread_count(project, request.user)
    activity_category_counts = activity_service.get_category_counts(project, request.user)

    return render(request, 'core/project_detail.html', {
        'project': project,
        'admins': admins,
        'progress_updates': progress_updates,
        'total_count': total_count,
        'funded_count': funded_count,
        'released_count': released_count,
        'has_unfunded_milestones': has_unfunded_milestones,
        'has_processing_milestones': has_processing_milestones,
        'processing_count': processing_count,
        'project_activities': project_activities,
        'activity_unread_count': activity_unread_count,
        'activity_category_counts': activity_category_counts,
        'project_activity_mark_read_url': reverse('core:project_activity_mark_read', args=[project.project_id]),
    })


@require_auth
def submit_project(request):
    """Project submission"""
    if not (request.user.role == 'client' or request.user.is_sub_admin):
        return render(request, 'core/access_denied.html', status=403)
    if request.method == 'POST':
        service = ProjectSubmissionService()
        
        attachment = request.FILES.get('attachment')
        attachment_filename = attachment.name if attachment else None
        
        result = service.submit_project(
            client=request.user,
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            stage=request.POST.get('stage'),
            support_type=request.POST.get('support_type'),
            research_area=request.POST.get('research_area'),
            confirms_lawful_use=bool(request.POST.get('confirms_lawful_use')),
            confirms_data_rights=bool(request.POST.get('confirms_data_rights')),
            irb_approval_provided=bool(request.POST.get('irb_approval_provided')),
            sample_size=request.POST.get('sample_size') or None,
            preferred_methods=request.POST.get('preferred_methods'),
            deadline_range=request.POST.get('deadline_range'),
            budget_range=request.POST.get('budget_range'),
            attachment=attachment,
            attachment_filename=attachment_filename,
            tenant_admin=request.user if request.user.is_sub_admin else None,
        )
        
        if result.success:
            AuditService.log(
                action='project_submitted',
                user=request.user,
                project=result.project
            )
            return redirect('core:project_detail', project_id=result.project.project_id)
        else:
            messages.error(request, result.error)

    return render(request, 'core/submit_project.html', {
        'deadline_range_choices': Project.DEADLINE_RANGE_CHOICES,
        'budget_range_choices': Project.BUDGET_RANGE_CHOICES,
    })


@require_analyst
def analyst_project_detail(request, project_id):
    """Analyst views assigned project"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if project.assigned_analyst != request.user:
        return render(request, 'core/access_denied.html', status=403)
    if request.user.parent_admin_id and project.tenant_admin_id != request.user.parent_admin_id:
        return render(request, 'core/access_denied.html', status=403)
    
    from apps.users.repositories import UserRepository
    admins = UserRepository.get_admins()
    progress_updates = ProjectProgress.objects.filter(project=project).order_by('-uploaded_at')
    activity_service = ProjectActivityService()
    project_activities = activity_service.get_project_activities(project, request.user, limit=40)
    activity_unread_count = activity_service.get_unread_count(project, request.user)
    activity_category_counts = activity_service.get_category_counts(project, request.user)
    
    return render(request, 'core/analyst_project_detail.html', {
        'project': project,
        'user': request.user,
        'admins': admins,
        'progress_updates': progress_updates,
        'project_activities': project_activities,
        'activity_unread_count': activity_unread_count,
        'activity_category_counts': activity_category_counts,
        'project_activity_mark_read_url': reverse('core:project_activity_mark_read', args=[project.project_id]),
    })



@require_analyst
def analyst_upload_deliverable(request, project_id):
    """Analyst uploads deliverable"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if project.assigned_analyst != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        deliverable_type = request.POST.get('type')
        description = request.POST.get('description', '')
        file = request.FILES.get('file')
        
        if not file or not deliverable_type:
            return JsonResponse({'error': 'Missing file or type'}, status=400)
        
        service = DeliverableService()
        deliverable, error = service.upload_deliverable(
            project=project,
            deliverable_type=deliverable_type,
            file=file,
            description=description,
            uploaded_by=request.user
        )
        
        if error:
            return JsonResponse({'error': error}, status=400)
        
        # Update project status
        project.status = 'qa'
        project.save()
        
        ChatService().create_system_message(
            project,
            f'Analyst submitted deliverable: {deliverable.get_deliverable_type_display()}'
        )
        
        AuditService.log(
            action='deliverable_uploaded',
            user=request.user,
            project=project,
            details={'deliverable_type': deliverable_type}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Deliverable uploaded successfully',
            'deliverable_id': str(deliverable.id)
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@require_analyst
def analyst_submit_work(request, project_id):
    """Analyst submits work for review"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if project.assigned_analyst != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        service = ProjectWorkflowService()
        result = service.submit_for_review(project)
        
        if not result.success:
            return JsonResponse({'error': result.error}, status=400)
        
        ChatService().create_system_message(project, 'Analyst submitted work for admin review')
        
        AuditService.log(
            action='work_submitted',
            user=request.user,
            project=project,
            details={'analyst': request.user.alias}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Work submitted for admin review'
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# Milestone Views
@require_admin
def create_milestone(request, project_id):
    """Admin creates a milestone"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if request.method == 'POST':
        try:
            service = MilestoneService()
            result = service.create_milestone(
                project=project,
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                amount=Decimal(request.POST.get('amount', 0)),
                due_date=request.POST.get('due_date'),
                delivery_instructions=request.POST.get('delivery_instructions', '')
            )
            
            if result.success:
                AuditService.log(
                    action='milestone_created',
                    user=request.user,
                    project=project,
                    details={
                        'milestone_id': str(result.milestone.id),
                        'title': result.milestone.title,
                        'amount': float(result.milestone.amount),
                        'due_date': str(result.milestone.due_date)
                    }
                )
                messages.success(request, f'Milestone "{result.milestone.title}" created successfully')
            else:
                messages.error(request, result.error)
                
        except (ValueError, TypeError) as e:
            messages.error(request, f'Error creating milestone: {str(e)}')
        
        return redirect('core:project_triage', project_id=project_id)


@require_admin
@require_POST
def update_milestone_status(request, milestone_id):
    """Update milestone work status"""
    milestone = get_object_or_404(Milestone, id=milestone_id)
    if request.user.is_sub_admin and milestone.project.tenant_admin_id != request.user.id:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    new_status = request.POST.get('status')
    
    service = MilestoneService()
    result = service.update_status(milestone, new_status)
    
    if not result.success:
        return JsonResponse({'success': False, 'error': result.error})
    
    AuditService.log(
        action='milestone_status_updated',
        user=request.user,
        project=milestone.project,
        milestone=milestone,
        details={'new_status': new_status}
    )
    
    return JsonResponse({'success': True, 'new_status': milestone.get_status_display()})


@require_admin
@require_POST
def approve_milestone(request, milestone_id):
    """Approve a completed milestone"""
    milestone = get_object_or_404(Milestone, id=milestone_id)
    if request.user.is_sub_admin and milestone.project.tenant_admin_id != request.user.id:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    service = MilestoneService()
    result = service.approve_milestone(milestone)
    
    if not result.success:
        return JsonResponse({'success': False, 'error': result.error})
    
    AuditService.log(
        action='milestone_approved',
        user=request.user,
        project=milestone.project,
        milestone=milestone,
        details={'title': milestone.title, 'amount': float(milestone.amount)}
    )
    
    # Check if Paystack payment was auto-released
    if milestone.payment_status == 'released':
        AuditService.log(
            action='paystack_payment_released',
            user=request.user,
            project=milestone.project,
            milestone=milestone,
            details={'title': milestone.title, 'amount': float(milestone.amount)}
        )
    
    return JsonResponse({
        'success': True, 
        'message': f'Milestone "{milestone.title}" approved',
        'is_releasable': milestone.is_releasable
    })


# Admin Project Views
@require_admin
def project_triage(request, project_id):
    """Admin project management view"""
    project = get_object_or_404(Project, project_id=project_id)
    if request.user.is_main_admin and project.tenant_admin_id is not None:
        return render(request, 'core/access_denied.html', status=403)
    if request.user.is_sub_admin and project.tenant_admin_id != request.user.id:
        return render(request, 'core/access_denied.html', status=403)
    
    milestones = project.milestones.all().order_by('created_at')
    from apps.audit.models import AuditLog
    audit_logs = AuditLog.objects.filter(project=project).order_by('-created_at')[:10]
    progress_reports = ProjectProgress.objects.filter(project=project).order_by('-uploaded_at')
    
    from apps.users.repositories import UserRepository
    analysts = UserRepository.get_analysts(parent_admin=request.user if (request.user.is_sub_admin or request.user.is_main_admin) else None)
    admins = UserRepository.get_admins()
    
    status_choices = Project.STATUS_CHOICES
    milestone_status_choices = Milestone.STATUS_CHOICES
    payment_status_choices = Milestone.PAYMENT_STATUS_CHOICES
    activity_service = ProjectActivityService()
    project_activities = activity_service.get_project_activities(project, request.user, limit=40)
    activity_unread_count = activity_service.get_unread_count(project, request.user)
    activity_category_counts = activity_service.get_category_counts(project, request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        workflow_service = ProjectWorkflowService()
        milestone_service = MilestoneService()
        
        if action == 'set_price':
            try:
                agreed_price = Decimal(request.POST.get('agreed_price', 0))
                result = workflow_service.set_price(project, agreed_price)
                if result.success:
                    AuditService.log_from_request('price_set', request, project, details={'price': float(agreed_price)})
                    messages.success(request, f'Project price set to ${agreed_price}')
                else:
                    messages.error(request, result.error)
            except (ValueError, TypeError):
                messages.error(request, 'Invalid price format')
                
        elif action == 'update_status':
            new_status = request.POST.get('status')
            if new_status and new_status in dict(Project.STATUS_CHOICES):
                old_status = project.status
                project.status = new_status
                project.save()
                AuditService.log_from_request('status_changed', request, project, 
                    details={'old_status': old_status, 'new_status': new_status})
                messages.success(request, f'Project status updated to {project.get_status_display()}')
                
        elif action == 'assign':
            analyst_id = request.POST.get('analyst_id')
            if analyst_id:
                try:
                    analyst = PseudonymousUser.objects.get(id=analyst_id, is_analyst=True)
                    result = workflow_service.assign_analyst(project, analyst, acting_user=request.user)
                    if result.success:
                        AuditService.log_from_request('analyst_assigned', request, project,
                            details={'analyst_alias': analyst.alias})
                        messages.success(request, f'Project assigned to {analyst.alias}')
                    else:
                        messages.error(request, result.error)
                except PseudonymousUser.DoesNotExist:
                    messages.error(request, 'Invalid analyst selected')
                    
        elif action == 'accept':
            result = workflow_service.accept_project(project)
            AuditService.log_from_request('project_accepted', request, project)
            messages.success(request, 'Project accepted')
            
        elif action == 'reject':
            result = workflow_service.reject_project(project)
            AuditService.log_from_request('project_rejected', request, project)
            messages.success(request, 'Project rejected')
            
        elif action == 'update_milestone_status':
            milestone_id = request.POST.get('milestone_id')
            new_status = request.POST.get('status')
            try:
                milestone = Milestone.objects.get(id=milestone_id, project=project)
                result = milestone_service.update_status(milestone, new_status)
                if result.success:
                    AuditService.log_from_request('milestone_status_changed', request, project,
                        milestone=milestone, details={'new_status': new_status})
                    messages.success(request, 'Milestone status updated successfully')
                else:
                    messages.error(request, result.error)
            except Milestone.DoesNotExist:
                messages.error(request, 'Milestone not found')
                
        elif action == 'release_milestone_payment':
            milestone_id = request.POST.get('milestone_id')
            from apps.payments.views import release_milestone_payment
            return release_milestone_payment(request, milestone_id)
    
    return render(request, 'core/project_triage.html', {
        'project': project,
        'milestones': milestones,
        'audit_logs': audit_logs,
        'analysts': analysts,
        'admins': admins,
        'status_choices': status_choices,
        'milestone_status_choices': milestone_status_choices,
        'payment_status_choices': payment_status_choices,
        'progress_reports': progress_reports,
        'project_activities': project_activities,
        'activity_unread_count': activity_unread_count,
        'activity_category_counts': activity_category_counts,
        'project_activity_mark_read_url': reverse('core:project_activity_mark_read', args=[project.project_id]),
    })


@require_admin
def admin_upload_progress(request, project_id):
    """Admin uploads PDF progress for a project"""
    project = get_object_or_404(Project, project_id=project_id)
    if request.user.is_sub_admin and project.tenant_admin_id != request.user.id:
        return render(request, 'core/access_denied.html', status=403)

    if request.method == "POST":
        uploaded_file = request.FILES.get("progress_file")
        if uploaded_file and uploaded_file.name.endswith(".pdf"):
            # Only pass fields that exist in your model
            ProjectProgress.objects.create(project=project, file=uploaded_file)
            AuditService.log_from_request(
                'progress_uploaded',
                request,
                project,
                details={'filename': uploaded_file.name}
            )
            messages.success(request, "Progress PDF uploaded successfully.")
        else:
            messages.error(request, "Please upload a valid PDF file.")

    return redirect("core:project_triage", project_id=project_id)

@require_auth
def view_progress_pdf(request, progress_id, project_id=None):
    """View progress PDF - accessible by both admin and client"""
    progress = get_object_or_404(ProjectProgress, id=progress_id)
    project = progress.project
    if project_id and project.project_id != project_id:
        raise Http404("Progress file does not belong to this project.")
    
    # Check permissions (same as above)
    if request.user.is_staff:
        pass
    elif hasattr(request.user, 'client_profile') and request.user.client_profile == project.client:
        pass
    else:
        messages.error(request, "You don't have permission to view this file.")
        return redirect("core:dashboard")
    
    return render(request, "core/view_progress_pdf.html", {"progress": progress})


@require_admin
def admin_project_review(request, project_id):
    """Admin reviews project"""
    project = get_object_or_404(Project, project_id=project_id)
    if request.user.is_main_admin and project.tenant_admin_id is not None:
        return render(request, 'core/access_denied.html', status=403)
    if request.user.is_sub_admin and project.tenant_admin_id != request.user.id:
        return render(request, 'core/access_denied.html', status=403)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        workflow_service = ProjectWorkflowService()
        
        if action == 'accept':
            result = workflow_service.accept_project(project)
            ChatService().create_system_message(project, 'Admin accepted the project. Ready for negotiation.')
            AuditService.log_from_request('project_accepted', request, project)
            return JsonResponse({'success': True, 'message': 'Project accepted'})
        
        elif action == 'reject':
            reason = request.POST.get('reason', 'No reason provided')
            result = workflow_service.reject_project(project, reason)
            ChatService().create_system_message(project, f'Project rejected. Reason: {reason}')
            AuditService.log_from_request('project_rejected', request, project, details={'reason': reason})
            return JsonResponse({'success': True, 'message': 'Project rejected'})
    
    from apps.negotiations.models import ProjectNegotiation
    from apps.messaging.models import Message
    
    negotiation = ProjectNegotiation.objects.filter(project=project).first()
    chat_messages = Message.objects.filter(project=project).order_by('created_at')
    
    return render(request, 'core/admin_project_review.html', {
        'project': project,
        'negotiation': negotiation,
        'messages': chat_messages,
        'user': request.user
    })


@require_admin
def admin_assign_analyst(request, project_id):
    """Admin assigns analyst to project"""
    project = get_object_or_404(Project, project_id=project_id)
    if request.user.is_main_admin and project.tenant_admin_id is not None:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    if request.user.is_sub_admin and project.tenant_admin_id != request.user.id:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        analyst_id = request.POST.get('analyst_id')
        
        try:
            analyst = PseudonymousUser.objects.get(id=analyst_id, is_analyst=True)
            workflow_service = ProjectWorkflowService()
            result = workflow_service.assign_analyst(project, analyst, acting_user=request.user)
            
            if result.success:
                ChatService().create_system_message(project, f'Project assigned to analyst: {analyst.alias}')
                AuditService.log_from_request('analyst_assigned', request, project,
                    details={'analyst_id': str(analyst.id), 'analyst_alias': analyst.alias})
                return JsonResponse({'success': True, 'message': f'Project assigned to {analyst.alias}'})
            else:
                return JsonResponse({'error': result.error}, status=400)
        
        except PseudonymousUser.DoesNotExist:
            return JsonResponse({'error': 'Analyst not found'}, status=404)
    
    from apps.users.repositories import UserRepository
    analysts = UserRepository.get_analysts(parent_admin=request.user if (request.user.is_sub_admin or request.user.is_main_admin) else None)
    
    return render(request, 'core/admin_assign_analyst.html', {
        'project': project,
        'analysts': analysts,
        'user': request.user
    })


@require_admin
def admin_review_deliverable(request, project_id):
    """Admin reviews deliverable"""
    project = get_object_or_404(Project, project_id=project_id)
    if request.user.is_sub_admin and project.tenant_admin_id != request.user.id:
        return render(request, 'core/access_denied.html', status=403)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        workflow_service = ProjectWorkflowService()
        
        if action == 'approve':
            result = workflow_service.approve_deliverable(project)
            ChatService().create_system_message(project, 'Admin approved deliverable. Project completed.')
            AuditService.log_from_request('deliverable_approved', request, project)
            return JsonResponse({'success': True, 'message': 'Deliverable approved'})
        
        elif action == 'reject':
            reason = request.POST.get('reason', 'No reason provided')
            result = workflow_service.reject_deliverable(project, reason)
            ChatService().create_system_message(project, f'Deliverable rejected. Reason: {reason}')
            AuditService.log_from_request('deliverable_rejected', request, project, details={'reason': reason})
            return JsonResponse({'success': True, 'message': 'Deliverable rejected'})
    
    deliverables = project.deliverables.all()
    
    return render(request, 'core/admin_review_deliverable.html', {
        'project': project,
        'deliverables': deliverables,
        'user': request.user
    })


@sub_admin_required
def sub_admin_project_list(request):
    projects = Project.objects.filter(tenant_admin=request.user, is_active=True).order_by('-created_at')
    status = request.GET.get('status', '').strip()
    if status:
        projects = projects.filter(status=status)
    return render(request, 'core/sub_admin_project_list.html', {
        'user': request.user,
        'projects': projects,
        'status': status,
        'status_choices': Project.STATUS_CHOICES,
    })


@sub_admin_required
def sub_admin_project_manage(request, project_id):
    project = get_object_or_404(Project, project_id=project_id, tenant_admin=request.user)
    milestones = project.milestones.all().order_by('created_at')
    from apps.users.repositories import UserRepository
    analysts = UserRepository.get_analysts(parent_admin=request.user)
    from apps.audit.models import AuditLog
    audit_logs = AuditLog.objects.filter(project=project).order_by('-created_at')[:10]
    activity_service = ProjectActivityService()
    project_activities = activity_service.get_project_activities(project, request.user, limit=40)
    activity_unread_count = activity_service.get_unread_count(project, request.user)
    activity_category_counts = activity_service.get_category_counts(project, request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        workflow_service = ProjectWorkflowService()
        milestone_service = MilestoneService()
        if action == 'assign':
            analyst_id = request.POST.get('analyst_id')
            try:
                analyst = PseudonymousUser.objects.get(id=analyst_id, is_analyst=True, parent_admin=request.user)
                result = workflow_service.assign_analyst(project, analyst, acting_user=request.user)
                if result.success:
                    AuditService.log_from_request('analyst_assigned', request, project, details={'analyst_alias': analyst.alias})
                    messages.success(request, f'Assigned to {analyst.alias}.')
                else:
                    messages.error(request, result.error)
            except PseudonymousUser.DoesNotExist:
                messages.error(request, 'Invalid analyst selected.')
        elif action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in dict(Project.STATUS_CHOICES):
                old_status = project.status
                project.status = new_status
                project.save()
                AuditService.log_from_request('status_changed', request, project, details={'old_status': old_status, 'new_status': new_status})
                messages.success(request, 'Project status updated.')
        elif action == 'create_milestone':
            result = milestone_service.create_milestone(
                project=project,
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                amount=Decimal(request.POST.get('amount', 0)),
                due_date=request.POST.get('due_date'),
                delivery_instructions=request.POST.get('delivery_instructions', '')
            )
            if result.success:
                AuditService.log_from_request('milestone_created', request, project, details={'milestone_id': str(result.milestone.id), 'title': result.milestone.title, 'amount': float(result.milestone.amount), 'due_date': str(result.milestone.due_date)})
                messages.success(request, 'Milestone created.')
            else:
                messages.error(request, result.error)
        return redirect('core:sub_admin_project_manage', project_id=project.project_id)

    return render(request, 'core/sub_admin_project_manage.html', {
        'user': request.user,
        'project': project,
        'milestones': milestones,
        'analysts': analysts,
        'audit_logs': audit_logs,
        'status_choices': Project.STATUS_CHOICES,
        'project_activities': project_activities,
        'activity_unread_count': activity_unread_count,
        'activity_category_counts': activity_category_counts,
        'project_activity_mark_read_url': reverse('core:project_activity_mark_read', args=[project.project_id]),
    })


@require_auth
@require_POST
def project_activity_mark_read(request, project_id):
    """Mark project activities as read for the current recipient."""
    project = get_object_or_404(Project, project_id=project_id)

    if project.client_id != request.user.id and project.tenant_admin_id != request.user.id and project.assigned_analyst_id != request.user.id and not request.user.is_admin:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    activity_ids = []
    if request.body:
        import json
        try:
            payload = json.loads(request.body.decode('utf-8'))
            activity_ids = payload.get('activity_ids') or []
        except Exception:
            activity_ids = []

    activity_service = ProjectActivityService()
    updated = activity_service.mark_read(project, request.user, activity_ids=activity_ids or None)
    unread_count = activity_service.get_unread_count(project, request.user)

    return JsonResponse({
        'success': True,
        'updated': updated,
        'unread_count': unread_count,
    })
