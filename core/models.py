"""
Core Models Module - Backward Compatibility Layer
Re-exports models from domain apps for existing imports
"""
import uuid
from django.db import models

# Re-export all models for backward compatibility
from apps.users.models import (
    PseudonymousUser,
    AuthToken,
    hash_email,
    check_email_hash,
)

from apps.projects.models import (
    Project,
    Milestone,
    ProjectFile,
    Deliverable,
    ProjectProgress,
    generate_project_id,
)

from apps.payments.models import (
    MilestonePayment,
)

from apps.messaging.models import (
    Message,
)

from apps.audit.models import (
    AuditLog,
)

from apps.negotiations.models import (
    ProjectNegotiation,
)


class DownloadToken(models.Model):
    """Download tokens for deliverables"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deliverable = models.ForeignKey(
        'projects.Deliverable', 
        on_delete=models.CASCADE, 
        related_name='download_tokens'
    )
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_downloadtoken'
    
    def is_valid(self):
        from django.utils import timezone
        return not self.used and timezone.now() < self.expires_at
