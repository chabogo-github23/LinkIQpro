"""
Users Domain Repository
Single Responsibility: Data access for user entities
"""
from typing import Optional, List
from django.utils import timezone
from django.db.models import Q
from .models import PseudonymousUser, AuthToken, hash_email


class UserRepository:
    """Repository for PseudonymousUser data access"""
    
    @staticmethod
    def get_by_id(user_id) -> Optional[PseudonymousUser]:
        try:
            return PseudonymousUser.objects.get(id=user_id)
        except PseudonymousUser.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_alias(alias: str) -> Optional[PseudonymousUser]:
        try:
            return PseudonymousUser.objects.get(alias=alias)
        except PseudonymousUser.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_email(email: str) -> Optional[PseudonymousUser]:
        if not email:
            return None
        hashed = hash_email(email)
        try:
            return PseudonymousUser.objects.get(email_hash=hashed)
        except PseudonymousUser.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_magic_token(token: str) -> Optional[PseudonymousUser]:
        try:
            return PseudonymousUser.objects.get(
                magic_token=token,
                magic_token_expires__gt=timezone.now()
            )
        except PseudonymousUser.DoesNotExist:
            return None
    
    @staticmethod
    def alias_exists(alias: str) -> bool:
        return PseudonymousUser.objects.filter(alias=alias).exists()
    
    @staticmethod
    def email_exists(email: str) -> bool:
        hashed = hash_email(email)
        return PseudonymousUser.objects.filter(email_hash=hashed).exists()
    
    @staticmethod
    def get_analysts(parent_admin: Optional[PseudonymousUser] = None) -> List[PseudonymousUser]:
        query = PseudonymousUser.objects.filter(is_analyst=True, is_active=True)
        if parent_admin:
            query = query.filter(parent_admin=parent_admin)
        return list(query)
    
    @staticmethod
    def get_admins() -> List[PseudonymousUser]:
        return list(PseudonymousUser.objects.filter(is_admin=True, is_sub_admin=False, is_active=True))
    
    @staticmethod
    def get_all_users(role_filter: str = 'all', search_query: str = '', acting_user: Optional[PseudonymousUser] = None):
        users = PseudonymousUser.objects.all()
        if acting_user and acting_user.is_sub_admin:
            users = users.filter(parent_admin=acting_user)
        elif acting_user and acting_user.is_main_admin:
            users = users.filter(Q(is_analyst=False) | Q(parent_admin=acting_user))
        
        if role_filter == 'client':
            users = users.filter(is_admin=False, is_analyst=False)
        elif role_filter == 'analyst':
            users = users.filter(is_analyst=True)
            if acting_user and acting_user.is_main_admin:
                users = users.filter(parent_admin=acting_user)
        elif role_filter == 'admin':
            users = users.filter(is_admin=True)
        elif role_filter == 'sub_admin':
            users = users.filter(is_sub_admin=True)
        
        if search_query:
            users = users.filter(alias__icontains=search_query)
        
        return users.order_by('-created_at')
    
    @staticmethod
    def get_user_counts(acting_user: Optional[PseudonymousUser] = None) -> dict:
        users = PseudonymousUser.objects.all()
        if acting_user and acting_user.is_sub_admin:
            users = users.filter(parent_admin=acting_user)
        elif acting_user and acting_user.is_main_admin:
            analyst_count = users.filter(is_analyst=True, parent_admin=acting_user).count()
            client_count = users.filter(is_admin=False, is_analyst=False, is_sub_admin=False).count()
            admin_count = users.filter(is_admin=True, is_sub_admin=False).count()
            sub_admin_count = users.filter(is_sub_admin=True).count()
            return {
                'total': analyst_count + client_count + admin_count + sub_admin_count,
                'clients': client_count,
                'analysts': analyst_count,
                'admins': admin_count,
                'sub_admins': sub_admin_count,
            }
        return {
            'total': users.count(),
            'clients': users.filter(is_admin=False, is_analyst=False, is_sub_admin=False).count(),
            'analysts': users.filter(is_analyst=True).count(),
            'admins': users.filter(is_admin=True, is_sub_admin=False).count(),
            'sub_admins': users.filter(is_sub_admin=True).count(),
        }
    
    @staticmethod
    def create_user(alias: str, email: str = None, password: str = None,
                   is_admin: bool = False, is_sub_admin: bool = False, is_analyst: bool = False,
                   parent_admin: Optional[PseudonymousUser] = None) -> PseudonymousUser:
        import secrets
        
        user = PseudonymousUser.objects.create(
            alias=alias,
            email_hash=hash_email(email) if email else None,
            is_admin=is_admin,
            is_sub_admin=is_sub_admin,
            is_analyst=is_analyst,
            parent_admin=parent_admin,
            magic_token=secrets.token_urlsafe(32),
            magic_token_expires=timezone.now() + timezone.timedelta(hours=24)
        )
        
        if password:
            user.set_password(password)
        
        return user
    
    @staticmethod
    def update_user(user: PseudonymousUser, **kwargs) -> PseudonymousUser:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.save()
        return user
    
    @staticmethod
    def delete_user(user: PseudonymousUser) -> bool:
        user.delete()
        return True


class AuthTokenRepository:
    """Repository for AuthToken data access"""
    
    @staticmethod
    def create_token(user: PseudonymousUser, hours_valid: int = 1) -> AuthToken:
        from django.utils.crypto import get_random_string
        
        return AuthToken.objects.create(
            user=user,
            token=get_random_string(48),
            expires_at=timezone.now() + timezone.timedelta(hours=hours_valid)
        )
    
    @staticmethod
    def get_valid_token(token: str) -> Optional[AuthToken]:
        try:
            auth_token = AuthToken.objects.get(token=token, used=False)
            if auth_token.is_valid():
                return auth_token
            return None
        except AuthToken.DoesNotExist:
            return None
    
    @staticmethod
    def invalidate_token(auth_token: AuthToken) -> None:
        auth_token.used = True
        auth_token.save()
