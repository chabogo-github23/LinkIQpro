"""
Audit Domain Services
"""
from typing import Optional
from .models import AuditLog
from apps.users.models import PseudonymousUser
from apps.projects.models import Project, Milestone


class AuditService:
    """Service for audit logging"""
    
    @staticmethod
    def log(action: str, user: PseudonymousUser = None, project: Project = None,
           milestone: Milestone = None, details: dict = None,
           ip_address: str = None, user_agent: str = None) -> AuditLog:
        """Create an audit log entry"""
        log = AuditLog.objects.create(
            user=user,
            project=project,
            milestone=milestone,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        AuditService._mirror_to_project_activity(log)
        return log
    
    @staticmethod
    def log_from_request(action: str, request, project: Project = None,
                        milestone: Milestone = None, details: dict = None) -> AuditLog:
        """Create an audit log entry from a request"""
        from apps.users.decorators import get_client_ip
        
        log = AuditLog.objects.create(
            user=getattr(request, 'user', None),
            project=project,
            milestone=milestone,
            action=action,
            details=details or {},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        AuditService._mirror_to_project_activity(log)
        return log
    
    @staticmethod
    def get_project_logs(project: Project, limit: int = 10):
        """Get recent audit logs for a project"""
        return AuditLog.objects.filter(project=project).order_by('-created_at')[:limit]
    
    @staticmethod
    def get_user_logs(user: PseudonymousUser, limit: int = 50):
        """Get recent audit logs for a user"""
        return AuditLog.objects.filter(user=user).order_by('-created_at')[:limit]

    @staticmethod
    def _mirror_to_project_activity(log: AuditLog):
        """Create unified project activity records for project-scoped audit logs."""
        if not log.project:
            return

        try:
            from apps.projects.services import ProjectActivityService
            ProjectActivityService.create_from_audit_log(log)
        except Exception:
            # Audit logging should never fail because activity mirroring failed.
            return
