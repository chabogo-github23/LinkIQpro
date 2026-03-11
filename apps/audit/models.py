"""
Audit Domain Models
- AuditLog: System-wide audit logging
"""
import uuid
from django.db import models


class AuditLog(models.Model):
    """Audit log for tracking all system actions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.PseudonymousUser', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='audit_logs'
    )
    project = models.ForeignKey(
        'projects.Project', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='audit_logs'
    )
    milestone = models.ForeignKey(
        'projects.Milestone', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'core_auditlog'
    
    def __str__(self):
        user_alias = self.user.alias if self.user else 'System'
        return f"{user_alias} - {self.action} - {self.created_at}"
