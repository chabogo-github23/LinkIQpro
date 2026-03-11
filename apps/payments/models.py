"""
Payments Domain Models
- MilestonePayment: Payment attempt tracking
"""
import uuid
from django.db import models


class MilestonePayment(models.Model):
    """Tracks payment attempts and history per milestone"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    milestone = models.ForeignKey(
        'projects.Milestone', 
        on_delete=models.CASCADE, 
        related_name='payment_attempts'
    )
    
    gateway = models.CharField(max_length=20, choices=[('paypal', 'PayPal'), ('paystack', 'PayStack')])
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    gateway_reference = models.CharField(max_length=255)  
    gateway_status = models.CharField(max_length=50)    
    metadata = models.JSONField(default=dict, blank=True)   
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'core_milestonepayment'
        indexes = [
            models.Index(fields=['milestone', 'gateway']),
            models.Index(fields=['gateway_reference']),
        ]
    
    def __str__(self):
        return f"{self.milestone.title} - {self.gateway} - {self.amount}"
