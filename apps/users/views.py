"""
Users Domain Views
Thin controllers that delegate to services
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q

from .models import PseudonymousUser
from .services import (
    UserRegistrationService,
    UserAuthenticationService,
    PasswordResetService,
    UserManagementService
)
from .decorators import (
    pseudonymous_user_required,
    admin_required,
    analyst_required,
    client_required,
    sub_admin_required,
    get_client_ip
)
from apps.audit.services import AuditService


def home(request):
    """Landing page"""
    return render(request, 'core/landing.html')


def register(request):
    """User registration"""
    if request.method == 'POST':
        alias = request.POST.get('alias', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if password != confirm_password:
            return render(request, 'auth/register.html', {
                'error': 'Passwords do not match.',
                'alias': alias,
                'email': email,
            })
        
        service = UserRegistrationService()
        result = service.register(alias, email, password)
        
        if not result.success:
            return render(request, 'auth/register.html', {
                'error': result.error,
                'alias': alias,
                'email': email,
            })
        
        AuditService.log(
            action='user_registered',
            user=result.user,
            details={'alias': result.user.alias},
            ip_address=get_client_ip(request)
        )
        
        messages.success(request, f"Registration successful! Welcome, {alias}. Please login to continue.")
        return redirect('core:request_magic_link')
    
    return render(request, 'auth/register.html')


def request_magic_link(request):
    """Login with alias and password, generate magic link"""
    if request.method == 'POST':
        alias = request.POST.get('alias')
        password = request.POST.get('password')

        if not alias or not password:
            return render(request, 'auth/request_magic_link.html', {
                'error': 'Alias and password are required.'
            })

        auth_service = UserAuthenticationService()
        result = auth_service.authenticate_with_password(alias, password)

        if not result.success:
            if PseudonymousUser.objects.filter(alias=alias).exists():
                return render(request, 'auth/request_magic_link.html', {
                    'error': result.error
                })
            else:
                messages.info(request, 'No account found. Please register first.')
                return redirect('core:register')

        magic_link = auth_service.generate_magic_link(result.user, request)
        
        AuditService.log(
            action='magic_link_requested',
            user=result.user,
            details={'alias': result.user.alias},
            ip_address=get_client_ip(request)
        )

        return render(request, 'auth/magic_link_display.html', {
            'magic_link': magic_link,
            'user': result.user,
        })

    return render(request, 'auth/request_magic_link.html')


def verify_magic_link(request):
    """Verify magic link token and log user in"""
    token = request.GET.get('token')
    if not token:
        return render(request, 'core/invalid_token.html', {'error': 'No token provided.'})

    auth_service = UserAuthenticationService()
    user = auth_service.verify_magic_token(token)
    
    if not user:
        return render(request, 'core/invalid_token.html', {'error': 'Invalid or expired magic link.'})

    auth_service.login_user(request, user)
    
    AuditService.log(
        action='user_logged_in',
        user=user,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )

    if user.is_sub_admin:
        return redirect('core:sub_admin_dashboard')
    if user.is_admin:
        return redirect('core:admin_dashboard')
    elif user.is_analyst:
        return redirect('core:analyst_dashboard')
    else:
        return redirect('core:client_dashboard')


def logout_view(request):
    """End user session"""
    auth_service = UserAuthenticationService()
    user = auth_service.logout_user(request)
    
    if user:
        AuditService.log(
            action='user_logged_out',
            user=user,
            ip_address=get_client_ip(request)
        )
    
    return redirect('core:home')


def password_reset_request(request):
    """Request password reset"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, "Email is required.")
            return redirect('core:password_reset_request')
        
        service = PasswordResetService()
        success, message = service.request_reset(email, request)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
        return redirect('core:password_reset_request')

    return render(request, 'auth/password_reset_form.html')


def password_reset_confirm(request, token):
    """Confirm password reset with token"""
    from .repositories import AuthTokenRepository
    
    auth_token = AuthTokenRepository.get_valid_token(token)
    
    if not auth_token:
        messages.error(request, "Invalid or expired link.")
        return redirect('core:password_reset_request')

    if request.method == 'POST':
        new_password = request.POST.get('password')
        
        service = PasswordResetService()
        success, message = service.confirm_reset(token, new_password)
        
        if success:
            messages.success(request, message)
            return redirect('core:request_magic_link')
        else:
            messages.error(request, message)
            return redirect('core:password_reset_confirm', token=token)

    return render(request, 'auth/password_reset_confirm.html', {"token": token})


# Dashboard Views
@client_required
def client_dashboard(request):
    """Client dashboard"""
    from apps.projects.repositories import ProjectRepository
    
    projects = ProjectRepository.get_client_projects(request.user)
    return render(request, 'core/client_dashboard.html', {
        'projects': projects,
        'user': request.user
    })


@analyst_required
def analyst_dashboard(request):
    """Analyst dashboard"""
    from apps.projects.repositories import ProjectRepository
    
    projects = ProjectRepository.get_analyst_projects(request.user)
    return render(request, 'core/analyst_dashboard.html', {
        'user': request.user,
        'assigned_projects': projects,
        'projects': projects,
    })


@admin_required
def admin_dashboard(request):
    """Admin dashboard"""
    from apps.projects.repositories import ProjectRepository
    
    users = PseudonymousUser.objects.all().order_by('-created_at') if request.user.is_main_admin else PseudonymousUser.objects.filter(parent_admin=request.user, is_analyst=True).order_by('-created_at')
    projects = ProjectRepository.get_all_projects(acting_user=request.user)
    
    user_service = UserManagementService()
    counts = user_service.get_user_stats(acting_user=request.user)
    
    return render(request, 'core/admin_dashboard.html', {
        'users': users,
        'projects': projects,
        'user': request.user,
        'total_users': counts['total'],
        'total_clients': counts['clients'],
        'total_analysts': counts['analysts'],
        'total_admins': counts['admins'],
    })


@sub_admin_required
def sub_admin_dashboard(request):
    """Sub-admin dashboard"""
    from apps.projects.models import Project

    projects = Project.objects.filter(tenant_admin=request.user, is_active=True).order_by('-created_at')
    analysts = PseudonymousUser.objects.filter(parent_admin=request.user, is_analyst=True).order_by('-created_at')
    counts = UserManagementService().get_user_stats(acting_user=request.user)

    return render(request, 'core/sub_admin_dashboard.html', {
        'user': request.user,
        'projects': projects,
        'analysts': analysts,
        'total_projects': projects.count(),
        'in_progress_projects': projects.filter(status='in_progress').count(),
        'completed_projects': projects.filter(status='completed').count(),
        'total_analysts': counts['analysts'],
    })


@sub_admin_required
def sub_admin_activities(request):
    """Sub-admin workspace activity feed"""
    from django.db.models import Q
    from apps.audit.models import AuditLog

    logs = AuditLog.objects.filter(
        Q(project__tenant_admin=request.user) |
        Q(user__parent_admin=request.user) |
        Q(user=request.user)
    ).select_related('user', 'project').order_by('-created_at')[:100]

    return render(request, 'core/sub_admin_activities.html', {
        'user': request.user,
        'logs': logs,
    })


@sub_admin_required
def sub_admin_analyst_list(request):
    analysts = PseudonymousUser.objects.filter(parent_admin=request.user, is_analyst=True).order_by('-created_at')
    search_query = request.GET.get('search', '').strip()
    if search_query:
        analysts = analysts.filter(alias__icontains=search_query)
    return render(request, 'core/sub_admin_analyst_list.html', {
        'user': request.user,
        'analysts': analysts,
        'search_query': search_query,
        'total_analysts': analysts.count(),
        'active_analysts': analysts.filter(is_active=True).count(),
    })


@sub_admin_required
def sub_admin_create_analyst(request):
    if request.method == 'POST':
        alias = request.POST.get('alias', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        if password != confirm_password:
            return render(request, 'core/sub_admin_create_analyst.html', {'error': 'Passwords do not match.', 'alias': alias, 'email': email, 'user': request.user})
        user, error = UserManagementService().create_user(alias, email, password, 'analyst', request.user)
        if error:
            return render(request, 'core/sub_admin_create_analyst.html', {'error': error, 'alias': alias, 'email': email, 'user': request.user})
        messages.success(request, f'Analyst "{user.alias}" created successfully.')
        return redirect('core:sub_admin_analyst_list')
    return render(request, 'core/sub_admin_create_analyst.html', {'user': request.user})


@sub_admin_required
def sub_admin_analyst_detail(request, user_id):
    analyst = get_object_or_404(PseudonymousUser, id=user_id, is_analyst=True, parent_admin=request.user)
    from apps.projects.models import Project
    projects = Project.objects.filter(Q(assigned_analyst=analyst) | Q(tenant_admin=request.user, assigned_analyst=analyst)).distinct().order_by('-created_at')
    return render(request, 'core/sub_admin_analyst_detail.html', {'user': request.user, 'analyst': analyst, 'projects': projects})


@sub_admin_required
def sub_admin_edit_analyst(request, user_id):
    analyst = get_object_or_404(PseudonymousUser, id=user_id, is_analyst=True, parent_admin=request.user)
    if request.method == 'POST':
        alias = request.POST.get('alias', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        new_password = request.POST.get('new_password', '').strip()
        success, error = UserManagementService().update_user(analyst, alias, 'analyst', is_active, request.user, new_password or None)
        if not success:
            return render(request, 'core/sub_admin_edit_analyst.html', {'user': request.user, 'analyst': analyst, 'error': error})
        messages.success(request, f'Analyst "{analyst.alias}" updated.')
        return redirect('core:sub_admin_analyst_detail', user_id=analyst.id)
    return render(request, 'core/sub_admin_edit_analyst.html', {'user': request.user, 'analyst': analyst})


# User Management Views
@admin_required
def admin_user_management(request):
    """Admin user management"""
    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '')
    
    from .repositories import UserRepository
    
    users = UserRepository.get_all_users(role_filter, search_query, acting_user=request.user)
    counts = UserRepository.get_user_counts(acting_user=request.user)
    
    return render(request, 'core/admin_user_management.html', {
        'users': users,
        'user': request.user,
        'role_filter': role_filter,
        'search_query': search_query,
        **counts
    })


@admin_required
def admin_user_detail(request, user_id):
    """View user details"""
    from apps.projects.models import Project
    
    target_user = get_object_or_404(PseudonymousUser, id=user_id)
    if request.user.is_sub_admin and target_user.parent_admin_id != request.user.id:
        return render(request, 'core/access_denied.html', status=403)
    if request.user.is_main_admin and target_user.is_analyst and target_user.parent_admin_id != request.user.id:
        return render(request, 'core/access_denied.html', status=403)
    
    if target_user.is_analyst:
        projects = Project.objects.filter(assigned_analyst=target_user).order_by('-created_at')
    else:
        projects = Project.objects.filter(client=target_user).order_by('-created_at')
    
    return render(request, 'core/admin_user_detail.html', {
        'target_user': target_user,
        'projects': projects,
        'role': target_user.role.title(),
        'user': request.user,
    })


@admin_required
def admin_create_user(request):
    """Admin creates a new user"""
    if request.method == 'POST':
        alias = request.POST.get('alias', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        role = request.POST.get('role', 'analyst' if request.user.is_sub_admin else 'client')
        
        if password != confirm_password:
            return render(request, 'core/admin_create_user.html', {
                'errors': ['Passwords do not match.'],
                'alias': alias,
                'email': email,
                'role': role,
                'user': request.user,
            })
        
        service = UserManagementService()
        user, error = service.create_user(alias, email, password, role, request.user)
        
        if error:
            return render(request, 'core/admin_create_user.html', {
                'errors': [error],
                'alias': alias,
                'email': email,
                'role': role,
                'user': request.user,
            })
        
        AuditService.log(
            action='user_created',
            user=request.user,
            details={'created_user': alias, 'role': role}
        )
        
        messages.success(request, f'User "{alias}" created successfully as {role.upper()}.')
        return redirect('core:admin_user_management')
    
    return render(request, 'core/admin_create_user.html', {'user': request.user})


@admin_required
def admin_edit_user(request, user_id):
    """Admin edits a user"""
    target_user = get_object_or_404(PseudonymousUser, id=user_id)
    if request.user.is_sub_admin and target_user.parent_admin_id != request.user.id:
        return render(request, 'core/access_denied.html', status=403)
    if request.user.is_main_admin and target_user.is_analyst and target_user.parent_admin_id != request.user.id:
        return render(request, 'core/access_denied.html', status=403)
    
    if request.method == 'POST':
        alias = request.POST.get('alias', '').strip()
        role = request.POST.get('role', 'client')
        is_active = request.POST.get('is_active') == 'on'
        new_password = request.POST.get('new_password', '').strip()
        
        service = UserManagementService()
        success, error = service.update_user(
            target_user, alias, role, is_active, request.user, new_password or None
        )
        
        if not success:
            return render(request, 'core/admin_edit_user.html', {
                'errors': [error],
                'target_user': target_user,
                'user': request.user,
            })
        
        AuditService.log(
            action='user_updated',
            user=request.user,
            details={'updated_user': alias, 'role': role}
        )
        
        messages.success(request, f'User "{alias}" updated successfully.')
        return redirect('core:admin_user_detail', user_id=user_id)
    
    return render(request, 'core/admin_edit_user.html', {
        'target_user': target_user,
        'current_role': target_user.role,
        'user': request.user,
    })


@admin_required
def admin_delete_user(request, user_id):
    """Admin deletes a user"""
    from apps.projects.models import Project
    
    target_user = get_object_or_404(PseudonymousUser, id=user_id)
    if request.user.is_sub_admin and target_user.parent_admin_id != request.user.id:
        return render(request, 'core/access_denied.html', status=403)
    if request.user.is_main_admin and target_user.is_analyst and target_user.parent_admin_id != request.user.id:
        return render(request, 'core/access_denied.html', status=403)
    
    if request.method == 'POST':
        service = UserManagementService()
        success, error = service.delete_user(target_user, request.user)
        
        if not success:
            messages.error(request, error)
            return redirect('core:admin_user_management')
        
        alias = target_user.alias
        
        AuditService.log(
            action='user_deleted',
            user=request.user,
            details={'deleted_user': alias}
        )
        
        messages.success(request, f'User "{alias}" has been deleted.')
        return redirect('core:admin_user_management')
    
    if target_user.is_analyst:
        project_count = Project.objects.filter(assigned_analyst=target_user).count()
    else:
        project_count = Project.objects.filter(client=target_user).count()
    
    return render(request, 'core/admin_delete_user.html', {
        'target_user': target_user,
        'project_count': project_count,
        'user': request.user,
    })

def privacy_policy(request):
    context = {
        'last_updated': 'December 10, 2025',
    
    }
  
    return render(request, 'core/privacy_policy.html', context)

def terms_of_service(request):
    context = {
        'last_updated': 'December 10, 2025'
    }
   
    return render(request, 'core/terms_of_service.html', context)
