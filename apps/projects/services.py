"""
Projects Domain Services
Business logic for project operations following SOLID principles
"""
from typing import Optional, Tuple, List
from dataclasses import dataclass
from decimal import Decimal
from django.utils import timezone

from .models import Project, Milestone, Deliverable
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
