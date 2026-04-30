"""
Users Domain Decorators
Access control decorators for views
"""
from functools import wraps
from django.shortcuts import redirect, render
from django.http import JsonResponse
from .models import PseudonymousUser


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_current_user(request):
    """Get the current pseudonymous user from session"""
    user_id = request.session.get('pseudonymous_user_id')
    if not user_id:
        return None
    try:
        return PseudonymousUser.objects.get(id=user_id)
    except PseudonymousUser.DoesNotExist:
        return None


def pseudonymous_user_required(view_func):
    """Decorator requiring authenticated pseudonymous user"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return redirect('core:request_magic_link')
        if not user.is_active:
            return redirect('core:request_magic_link')
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Decorator requiring admin role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return redirect('core:request_magic_link')
        if not user.is_active:
            return redirect('core:request_magic_link')
        if not user.is_admin:
            return render(request, 'core/access_denied.html', status=403)
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def main_admin_required(view_func):
    """Decorator requiring main admin role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return redirect('core:request_magic_link')
        if not user.is_active or not user.is_main_admin:
            return render(request, 'core/access_denied.html', status=403)
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def analyst_required(view_func):
    """Decorator requiring analyst role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return redirect('core:request_magic_link')
        if not user.is_active:
            return redirect('core:request_magic_link')
        if not user.is_analyst:
            return render(request, 'core/access_denied.html', status=403)
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def sub_admin_required(view_func):
    """Decorator requiring sub-admin role"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return redirect('core:request_magic_link')
        if not user.is_active:
            return redirect('core:request_magic_link')
        if not user.is_sub_admin:
            return render(request, 'core/access_denied.html', status=403)
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def client_required(view_func):
    """Decorator requiring client role (non-admin, non-analyst)"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return redirect('core:request_magic_link')
        if not user.is_active:
            return redirect('core:request_magic_link')
        if user.is_admin or user.is_analyst:
            return render(request, 'core/access_denied.html', status=403)
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper
