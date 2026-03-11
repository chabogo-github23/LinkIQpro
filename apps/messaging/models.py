import uuid
from django.db import models


class Message(models.Model):
    """Chat messages between client, analyst, and admin"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('file', 'File'),
        ('proposal', 'Price Proposal'),
        ('agreement', 'Agreement'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'projects.Project', 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        'users.PseudonymousUser', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        'users.PseudonymousUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_messages'
    )
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='chat_files/%Y/%m/%d/', blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        db_table = 'core_message'
    
    def __str__(self):
        sender_alias = self.sender.alias if self.sender else 'System'
        return f"{self.project.project_id} - {sender_alias}"
