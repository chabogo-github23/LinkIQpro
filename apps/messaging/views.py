"""
Messaging Domain Views
"""
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.projects.models import Project
from apps.users.models import PseudonymousUser
from apps.users.decorators import pseudonymous_user_required as require_auth
from apps.audit.services import AuditService
from .services import ChatService


@require_auth
@require_http_methods(["GET", "POST"])
def project_chat(request, project_id):
    """Project chat view"""
    project = get_object_or_404(Project, project_id=project_id)
    user = request.user

    # Permission check
    if not (project.client == user or project.assigned_analyst == user or user.is_admin or project.tenant_admin_id == user.id):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    chat_service = ChatService()

    if request.method == 'POST':
        message_content = request.POST.get('message', '').strip()
        receiver_id = request.POST.get('receiver_id')
        uploaded_file = request.FILES.get('file')

        if not receiver_id:
            return JsonResponse({'error': 'Missing receiver'}, status=400)

        receiver = get_object_or_404(PseudonymousUser, id=receiver_id)
        
        message, error = chat_service.send_message(
            project=project,
            sender=user,
            receiver=receiver,
            content=message_content,
            file=uploaded_file
        )
        
        if error:
            return JsonResponse({'error': error}, status=403)

        AuditService.log_from_request(
            'message_sent',
            request,
            project,
            details={
                'message_type': message.message_type,
                'filename': message.filename,
                'receiver_id': str(receiver.id),
                'receiver_alias': receiver.alias,
            }
        )

        file_url = None
        if message.file:
            # Build absolute URL for the file
            file_url = request.build_absolute_uri(message.file.url)

        return JsonResponse({
            'success': True,
            'message': {
                'id': str(message.id),
                'sender': user.alias,
                'sender_id': str(user.id),
                'receiver': receiver.alias,
                'content': message.content,
                'message_type': message.message_type,
                'file_url': file_url,
                'filename': message.filename,
                'created_at': message.created_at.isoformat(),
            }
        })

    # GET request - fetch messages
    receiver_id = request.GET.get('receiver_id')
    
    if receiver_id:
        try:
            target_user = get_object_or_404(PseudonymousUser, id=receiver_id)
            messages_data = chat_service.get_conversation(project, user, target_user)
            
            # Build absolute URLs for files
            for msg in messages_data:
                if msg.get('file_url'):
                    # Convert relative URL to absolute URL
                    msg['file_url'] = request.build_absolute_uri(msg['file_url'])
                # Ensure sender_id is string for JavaScript comparison
                if 'sender_id' in msg:
                    msg['sender_id'] = str(msg['sender_id'])
        except Exception as e:
            print(f"Error fetching conversation: {e}")
            messages_data = []
    else:
        messages_data = []

    targets = chat_service.get_chat_targets(project, user)

    return JsonResponse({
        'success': True,
        'messages': messages_data,
        'targets': targets
    })
