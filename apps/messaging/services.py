"""
Messaging Domain Services
"""
from typing import List, Dict, Any, Optional
from .models import Message
from .repositories import MessageRepository
from apps.projects.models import Project
from apps.users.models import PseudonymousUser


class ChatService:
    """Service for project chat functionality"""
    
    def __init__(self, message_repo: MessageRepository = None):
        self.message_repo = message_repo or MessageRepository()
    
    def send_message(self, project: Project, sender: PseudonymousUser,
                    receiver: PseudonymousUser, content: str = '',
                    file=None) -> tuple[Optional[Message], Optional[str]]:
        """Send a message with role-based validation"""
        
        # Validate chat permissions
        error = self._validate_chat_permission(project, sender, receiver)
        if error:
            return None, error
        
        # Determine message type
        if file:
            message_type = 'file'
            content = f"📎 {file.name}"
            filename = file.name
        else:
            message_type = 'text'
            filename = ''
        
        message = self.message_repo.create_message(
            project=project,
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            content=content,
            file=file,
            filename=filename
        )
        
        return message, None
    
    def _validate_chat_permission(self, project: Project, sender: PseudonymousUser,
                                  receiver: PseudonymousUser) -> Optional[str]:
        """Validate that sender can chat with receiver"""
        if sender.is_sub_admin:
            if receiver != project.assigned_analyst:
                return 'Sub-admin can only chat with assigned analyst'
        elif sender.is_admin:
            if receiver not in [project.client, project.assigned_analyst]:
                return 'Admin can only chat with client or analyst'
        elif sender == project.assigned_analyst:
            if project.tenant_admin:
                if receiver != project.tenant_admin:
                    return 'Analyst can only chat with their sub-admin for this project'
            elif not receiver.is_admin:
                return 'Analyst can only chat with admin'
        elif sender == project.client:
            if not receiver.is_admin:
                return 'Client can only chat with admin'
        else:
            return 'Invalid sender'
        
        return None
    
    def get_conversation(self, project: Project, user: PseudonymousUser,
                        target_user: PseudonymousUser) -> List[Dict[str, Any]]:
        """Get conversation between two users"""
        from django.db import models
        from .models import Message 
        
        # Query messages directly with file field
        messages = Message.objects.filter(
            project=project
        ).filter(
            models.Q(sender=user, receiver=target_user) |
            models.Q(sender=target_user, receiver=user)
        ).select_related('sender', 'receiver').order_by('created_at')
        
        conversation = []
        for msg in messages:
            message_data = {
                'id': str(msg.id),
                'sender': msg.sender.alias if msg.sender else 'System',
                'sender_id': str(msg.sender.id) if msg.sender else None,
                'receiver': msg.receiver.alias if msg.receiver else None,
                'content': msg.content,
                'message_type': msg.message_type,
                'filename': msg.filename,
                'created_at': msg.created_at.isoformat(),
                'file_url': None,
            }
            
            # Check if message has a file and get its URL
            if msg.file and hasattr(msg.file, 'url'):
                try:
                    message_data['file_url'] = msg.file.url
                    print(f"DEBUG: Found file URL for message {msg.id}: {msg.file.url}")
                except Exception as e:
                    print(f"DEBUG: Error getting file URL for message {msg.id}: {e}")
                    message_data['file_url'] = None
            
            conversation.append(message_data)
        
        print(f"DEBUG: Returning {len(conversation)} messages with file URLs")
        return conversation
    
    def get_chat_targets(self, project: Project, user: PseudonymousUser) -> List[Dict[str, str]]:
        """Get available chat targets for a user"""
        targets = []
        
        if user.is_sub_admin:
            if project.assigned_analyst and project.assigned_analyst.id != user.id:
                targets.append({'id': str(project.assigned_analyst.id), 'alias': project.assigned_analyst.alias})
        elif user.is_admin:
            if project.client and project.client.id != user.id:
                targets.append({'id': str(project.client.id), 'alias': project.client.alias})
            if project.assigned_analyst and project.assigned_analyst.id != user.id:
                targets.append({'id': str(project.assigned_analyst.id), 'alias': project.assigned_analyst.alias})
        
        elif user == project.assigned_analyst or user.is_analyst:
            if project.tenant_admin:
                targets.append({'id': str(project.tenant_admin.id), 'alias': project.tenant_admin.alias})
            else:
                admins = PseudonymousUser.objects.filter(is_admin=True, is_sub_admin=False).exclude(id=user.id)
                for admin in admins:
                    targets.append({'id': str(admin.id), 'alias': admin.alias})
                if project.client and project.client.id != user.id:
                    targets.append({'id': str(project.client.id), 'alias': project.client.alias})
        
        elif user == project.client:
            admins = PseudonymousUser.objects.filter(is_admin=True).exclude(id=user.id)
            for admin in admins:
                targets.append({'id': str(admin.id), 'alias': admin.alias})
            if project.assigned_analyst and project.assigned_analyst.id != user.id:
                targets.append({'id': str(project.assigned_analyst.id), 'alias': project.assigned_analyst.alias})
        
        return targets
    
    def create_system_message(self, project: Project, content: str) -> Message:
        """Create a system message"""
        return self.message_repo.create_system_message(project, content)
