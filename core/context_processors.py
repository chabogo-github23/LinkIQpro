from .models import PseudonymousUser

def chat_users(request):
    """Make admin users available for chat in all templates"""
    if request.user.is_authenticated:
        admins = PseudonymousUser.objects.filter(is_admin=True, is_active=True)
        return {
            'chat_admins': admins,
        }
    return {}
