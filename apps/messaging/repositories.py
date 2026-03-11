"""
Messaging Domain Repository
"""
from typing import List, Optional
from django.db.models import Q
from .models import Message
from apps.projects.models import Project
from apps.users.models import PseudonymousUser


class MessageRepository:
    """Repository for Message data access"""
    
    @staticmethod
    def get_project_messages(project: Project) -> List[Message]:
        return list(Message.objects.filter(project=project).order_by('created_at'))
    
    @staticmethod
    def get_conversation(project: Project, user1: PseudonymousUser, 
                        user2: PseudonymousUser) -> List[Message]:
        return list(Message.objects.filter(
            project=project
        ).filter(
            Q(sender=user1, receiver=user2) |
            Q(sender=user2, receiver=user1)
        ).select_related('sender', 'receiver').order_by('created_at'))
    
    @staticmethod
    def create_message(project: Project, sender: PseudonymousUser,
                      receiver: PseudonymousUser = None, message_type: str = 'text',
                      content: str = '', file=None, filename: str = '',
                      metadata: dict = None) -> Message:
        return Message.objects.create(
            project=project,
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            content=content,
            file=file,
            filename=filename,
            metadata=metadata or {}
        )
    
    @staticmethod
    def create_system_message(project: Project, content: str) -> Message:
        return Message.objects.create(
            project=project,
            sender=None,
            message_type='system',
            content=content
        )
