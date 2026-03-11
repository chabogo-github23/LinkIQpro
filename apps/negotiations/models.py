"""
Negotiations Domain Models
- ProjectNegotiation: Track negotiation state
"""
import uuid
from django.db import models


class ProjectNegotiation(models.Model):
    """Track negotiation state between client and admin"""
    NEGOTIATION_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('agreed', 'Agreed'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        'projects.Project', 
        on_delete=models.CASCADE, 
        related_name='negotiation'
    )
    status = models.CharField(max_length=20, choices=NEGOTIATION_STATUS, default='pending')
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    agreed_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    proposed_deadline = models.DateField(null=True, blank=True)
    agreed_deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    agreed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'core_projectnegotiation'
    
    def __str__(self):
        return f"Negotiation for {self.project.project_id}"
