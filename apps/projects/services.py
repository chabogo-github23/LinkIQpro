"""
Projects Domain Services
Business logic for project operations following SOLID principles
"""
from typing import Optional, Tuple, List
from dataclasses import dataclass
from decimal import Decimal
from django.utils import timezone
from django.db.utils import ProgrammingError, OperationalError

from .models import Project, Milestone, Deliverable, ProjectActivity
from .repositories import ProjectRepository, MilestoneRepository, DeliverableRepository


@dataclass
class ProjectResult:
    success: bool
    project: Optional[Project] = None
    error: Optional[str] = None


@dataclass
class MilestoneResult:
    success: bool
    milestone: Optional[Milestone] = None
    error: Optional[str] = None


class ProjectSubmissionService:
    """
    Service for project submission
    Single Responsibility: Handle new project creation
    """
    
    def __init__(self, project_repo: ProjectRepository = None):
        self.project_repo = project_repo or ProjectRepository()
    
    def submit_project(self, client, title: str, description: str, stage: str,
                      support_type: str, research_area: str, **kwargs) -> ProjectResult:
        """Submit a new project"""
        
        if not title or len(title) < 5:
            return ProjectResult(success=False, error='Title must be at least 5 characters.')
        
        if not description:
            return ProjectResult(success=False, error='Description is required.')
        
        project = self.project_repo.create_project(
            client=client,
            title=title,
            description=description,
            stage=stage,
            support_type=support_type,
            research_area=research_area,
            **kwargs
        )
        
        return ProjectResult(success=True, project=project)


class ProjectWorkflowService:
    """
    Service for project workflow management
    Single Responsibility: Handle project status transitions
    """
    
    def __init__(self, project_repo: ProjectRepository = None):
        self.project_repo = project_repo or ProjectRepository()
    
    def accept_project(self, project: Project) -> ProjectResult:
        """Admin accepts a project"""
        project = self.project_repo.update_status(project, 'accepted')
        return ProjectResult(success=True, project=project)
    
    def reject_project(self, project: Project, reason: str = None) -> ProjectResult:
        """Admin rejects a project"""
        project = self.project_repo.update_status(project, 'rejected')
        return ProjectResult(success=True, project=project)
    
    def assign_analyst(self, project: Project, analyst, acting_user=None) -> ProjectResult:
        """Assign an analyst to the project"""
        if not analyst.is_analyst:
            return ProjectResult(success=False, error='User is not an analyst.')
        if project.tenant_admin and analyst.parent_admin_id != project.tenant_admin_id:
            return ProjectResult(success=False, error='Analyst must belong to this sub-admin workspace.')
        if acting_user and getattr(acting_user, 'is_sub_admin', False) and project.tenant_admin_id != acting_user.id:
            return ProjectResult(success=False, error='You can only assign analysts to your own projects.')
        
        project = self.project_repo.assign_analyst(project, analyst)
        return ProjectResult(success=True, project=project)
    
    def submit_for_review(self, project: Project) -> ProjectResult:
        """Analyst submits work for review"""
        if not project.deliverables.exists():
            return ProjectResult(success=False, error='No deliverables uploaded.')
        
        project = self.project_repo.update_status(project, 'qa')
        return ProjectResult(success=True, project=project)
    
    def approve_deliverable(self, project: Project) -> ProjectResult:
        """Admin approves deliverable and completes project"""
        project = self.project_repo.update_status(project, 'completed')
        return ProjectResult(success=True, project=project)
    
    def reject_deliverable(self, project: Project, reason: str = None) -> ProjectResult:
        """Admin rejects deliverable for revision"""
        project = self.project_repo.update_status(project, 'qa')
        return ProjectResult(success=True, project=project)
    
    def set_price(self, project: Project, price: Decimal) -> ProjectResult:
        """Set the project price"""
        if price <= 0:
            return ProjectResult(success=False, error='Price must be greater than 0.')
        
        project = self.project_repo.update_project(project, total_price=price)
        return ProjectResult(success=True, project=project)


class MilestoneService:
    """
    Service for milestone management
    Single Responsibility: Handle milestone operations
    """
    
    def __init__(self, milestone_repo: MilestoneRepository = None):
        self.milestone_repo = milestone_repo or MilestoneRepository()
    
    def create_milestone(self, project: Project, title: str, description: str,
                        amount: Decimal, due_date, delivery_instructions: str = '') -> MilestoneResult:
        """Create a new milestone"""
        
        if not title:
            return MilestoneResult(success=False, error='Title is required.')
        
        if not description:
            return MilestoneResult(success=False, error='Description is required.')
        
        if amount <= 0:
            return MilestoneResult(success=False, error='Amount must be greater than 0.')
        
        if not due_date:
            return MilestoneResult(success=False, error='Due date is required.')
        
        milestone = self.milestone_repo.create_milestone(
            project=project,
            title=title,
            description=description,
            amount=amount,
            due_date=due_date,
            delivery_instructions=delivery_instructions
        )
        
        return MilestoneResult(success=True, milestone=milestone)
    
    def update_status(self, milestone: Milestone, status: str) -> MilestoneResult:
        """Update milestone work status"""
        valid_statuses = dict(Milestone.STATUS_CHOICES).keys()
        if status not in valid_statuses:
            return MilestoneResult(success=False, error='Invalid status.')
        
        milestone = self.milestone_repo.update_status(milestone, status)
        return MilestoneResult(success=True, milestone=milestone)
    
    def approve_milestone(self, milestone: Milestone) -> MilestoneResult:
        """Approve a completed milestone"""
        if milestone.status != 'completed':
            return MilestoneResult(success=False, error='Milestone must be completed before approval.')
        
        milestone = self.milestone_repo.update_status(milestone, 'approved')
        
        # Auto-release Paystack payments on approval
        if milestone.gateway_used == 'paystack' and milestone.payment_status == 'funded':
            milestone = self.milestone_repo.update_payment_status(milestone, 'released')
        
        return MilestoneResult(success=True, milestone=milestone)
    
    def get_payable_milestones(self, project: Project) -> List[Milestone]:
        """Get milestones that can be paid"""
        return self.milestone_repo.get_unfunded_milestones(project)


class DeliverableService:
    """
    Service for deliverable management
    Single Responsibility: Handle deliverable operations
    """
    
    def __init__(self, deliverable_repo: DeliverableRepository = None):
        self.deliverable_repo = deliverable_repo or DeliverableRepository()
    
    def upload_deliverable(self, project: Project, deliverable_type: str, 
                          file, description: str, uploaded_by) -> Tuple[Optional[Deliverable], Optional[str]]:
        """Upload a deliverable for a project"""
        
        if not file:
            return None, 'File is required.'
        
        if not deliverable_type:
            return None, 'Deliverable type is required.'
        
        deliverable = self.deliverable_repo.create_deliverable(
            project=project,
            deliverable_type=deliverable_type,
            file=file,
            filename=file.name,
            description=description,
            uploaded_by=uploaded_by
        )
        
        return deliverable, None


class ProjectActivityService:
    """Project activity creation and feed helpers."""

    ACTIVITY_SECTION_MAP = {
        'message': 'project-communication',
        'progress': 'project-progress',
        'file': 'project-deliverables',
        'payment': 'project-payments',
        'milestone': 'project-milestones',
        'review': 'project-communication',
        'deadline': 'project-overview',
        'completion': 'project-deliverables',
        'system': 'project-overview',
    }

    @staticmethod
    def _project_recipients(project: Project, actor=None) -> List:
        recipients = []
        for user in [project.client, project.tenant_admin, project.assigned_analyst, actor]:
            if user and user not in recipients:
                recipients.append(user)
        return recipients

    @classmethod
    def _normalize_targets(cls, activity_type: str, target_section: str = '') -> str:
        if target_section:
            return target_section
        return cls.ACTIVITY_SECTION_MAP.get(activity_type, 'project-overview')

    @classmethod
    def create_activity(
        cls,
        project: Project,
        activity_type: str,
        title: str,
        description: str = '',
        sender=None,
        related_object_id: str = None,
        target_section: str = '',
        url: str = None,
        recipients: List = None,
    ) -> List[ProjectActivity]:
        """Create a project activity for all relevant recipients."""
        if not project or not activity_type or not title:
            return []

        target_section = cls._normalize_targets(activity_type, target_section)
        recipient_list = recipients or cls._project_recipients(project, sender)
        created = []

        for recipient in recipient_list:
            created.append(ProjectActivity.objects.create(
                project=project,
                sender=sender,
                recipient=recipient,
                activity_type=activity_type,
                title=title,
                description=description or '',
                target_section=target_section,
                related_object_id=related_object_id,
                url=url,
                is_read=bool(sender and recipient and sender.id == recipient.id),
                read_at=timezone.now() if sender and recipient and sender.id == recipient.id else None,
            ))

        return created

    @classmethod
    def create_from_audit_log(cls, log):
        """Map an audit log entry to one or more project activities."""
        if not getattr(log, 'project', None):
            return []

        details = log.details or {}
        action_map = {
            'message_sent': ('message', 'New Message', 'A new project message was sent.', 'project-communication'),
            'project_submitted': ('system', 'Project Submitted', details.get('title', log.project.title), 'project-overview'),
            'project_accepted': ('system', 'Project Accepted', 'The project was accepted and moved forward.', 'project-overview'),
            'project_rejected': ('system', 'Project Rejected', details.get('reason', 'The project was rejected.'), 'project-overview'),
            'price_set': ('payment', 'Project Price Updated', f"Agreed price set to ${details.get('price', log.project.total_price)}.", 'project-payments'),
            'status_changed': ('system', 'Project Status Updated', f"Status changed to {details.get('new_status', log.project.status).replace('_', ' ').title()}.", 'project-overview'),
            'analyst_assigned': ('system', 'Analyst Assigned', f"Assigned to {details.get('analyst_alias', 'an analyst')}.", 'project-overview'),
            'milestone_created': ('milestone', 'Milestone Created', details.get('title', 'A new milestone was created.'), 'project-milestones'),
            'milestone_status_updated': ('milestone', 'Milestone Updated', f"Milestone moved to {details.get('new_status', 'a new status')}.", 'project-milestones'),
            'milestone_status_changed': ('milestone', 'Milestone Updated', f"Milestone moved to {details.get('new_status', 'a new status')}.", 'project-milestones'),
            'milestone_approved': ('review', 'Milestone Approved', details.get('title', 'A milestone was approved.'), 'project-milestones'),
            'deliverable_uploaded': ('file', 'Deliverable Uploaded', details.get('deliverable_type', 'A deliverable was uploaded.'), 'project-deliverables'),
            'deliverable_approved': ('completion', 'Deliverable Approved', 'The final deliverable was approved.', 'project-final-deliverables'),
            'deliverable_rejected': ('review', 'Deliverable Rejected', details.get('reason', 'The deliverable needs revision.'), 'project-final-deliverables'),
            'work_submitted': ('progress', 'Work Submitted', 'Work was submitted for review.', 'project-communication'),
            'progress_uploaded': ('progress', 'Progress Report Uploaded', details.get('filename', 'A progress report was uploaded.'), 'project-progress'),
            'paystack_payment_success': ('payment', 'Payment Completed', 'Milestone payment completed successfully.', 'project-payments'),
            'paystack_payment_failed': ('payment', 'Payment Failed', details.get('reason', 'The payment failed.'), 'project-payments'),
            'paypal_funds_held': ('payment', 'Funds Held in Escrow', 'Payment has been held in escrow.', 'project-payments'),
            'paypal_authorization_failed': ('payment', 'Payment Authorization Failed', details.get('error', 'PayPal authorization failed.'), 'project-payments'),
            'paypal_payment_captured': ('payment', 'Payment Released', 'Escrow funds were released.', 'project-payments'),
            'paystack_payment_released': ('payment', 'Payment Released', 'Payment was released to the project team.', 'project-payments'),
            'payment_cancelled': ('payment', 'Payment Cancelled', 'A milestone payment attempt was cancelled.', 'project-payments'),
            'project_delivered': ('completion', 'Project Delivered', 'Completed project deliverables were sent to the client.', 'project-deliverables'),
        }

        mapped = action_map.get(log.action)
        if not mapped:
            return []

        activity_type, title, description, target_section = mapped
        sender = log.user

        if log.action == 'message_sent':
            recipients = []
            if sender:
                recipients.append(sender)
            receiver_id = details.get('receiver_id')
            if receiver_id:
                try:
                    from apps.users.models import PseudonymousUser
                    receiver = PseudonymousUser.objects.filter(id=receiver_id).first()
                    if receiver and receiver not in recipients:
                        recipients.append(receiver)
                except Exception:
                    pass
            if not recipients:
                recipients = cls._project_recipients(log.project, sender)
            return cls.create_activity(
                project=log.project,
                activity_type=activity_type,
                title=title,
                description=description,
                sender=sender,
                target_section=target_section,
                recipients=recipients,
            )

        return cls.create_activity(
            project=log.project,
            activity_type=activity_type,
            title=title,
            description=description,
            sender=sender,
            target_section=target_section,
            recipients=recipients,
        )

    @staticmethod
    def get_project_activities(project: Project, recipient, limit: int = 50):
        try:
            return list(
                ProjectActivity.objects.filter(project=project, recipient=recipient)
                .select_related('sender', 'recipient')
                .order_by('-created_at')[:limit]
            )
        except (ProgrammingError, OperationalError):
            return []

    @staticmethod
    def get_unread_count(project: Project, recipient) -> int:
        try:
            return ProjectActivity.objects.filter(project=project, recipient=recipient, is_read=False).count()
        except (ProgrammingError, OperationalError):
            return 0

    @staticmethod
    def get_category_counts(project: Project, recipient) -> dict:
        try:
            queryset = ProjectActivity.objects.filter(project=project, recipient=recipient)
            counts = {
                'all': queryset.count(),
                'message': queryset.filter(activity_type='message').count(),
                'progress': queryset.filter(activity_type='progress').count(),
                'file': queryset.filter(activity_type='file').count(),
                'payment': queryset.filter(activity_type='payment').count(),
                'milestone': queryset.filter(activity_type='milestone').count(),
                'review': queryset.filter(activity_type='review').count(),
                'deadline': queryset.filter(activity_type='deadline').count(),
                'completion': queryset.filter(activity_type='completion').count(),
                'system': queryset.filter(activity_type='system').count(),
            }
            return counts
        except (ProgrammingError, OperationalError):
            return {
                'all': 0,
                'message': 0,
                'progress': 0,
                'file': 0,
                'payment': 0,
                'milestone': 0,
                'review': 0,
                'deadline': 0,
                'completion': 0,
                'system': 0,
            }

    @staticmethod
    def mark_read(project: Project, recipient, activity_ids: List[str] = None) -> int:
        try:
            queryset = ProjectActivity.objects.filter(project=project, recipient=recipient, is_read=False)
            if activity_ids:
                queryset = queryset.filter(id__in=activity_ids)
            updated = queryset.update(is_read=True, read_at=timezone.now())
            return updated
        except (ProgrammingError, OperationalError):
            return 0
