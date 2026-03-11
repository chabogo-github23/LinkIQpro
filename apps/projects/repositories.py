"""
Projects Domain Repository
Single Responsibility: Data access for project entities
"""
from typing import Optional, List
from decimal import Decimal
from django.utils import timezone
from .models import Project, Milestone, ProjectFile, Deliverable, ProjectProgress


class ProjectRepository:
    """Repository for Project data access"""
    
    @staticmethod
    def get_by_id(project_id) -> Optional[Project]:
        try:
            return Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_project_id(project_id: str) -> Optional[Project]:
        try:
            return Project.objects.get(project_id=project_id)
        except Project.DoesNotExist:
            return None
    
    @staticmethod
    def get_client_projects(client) -> List[Project]:
        return list(Project.objects.filter(client=client).order_by('-created_at'))
    
    @staticmethod
    def get_analyst_projects(analyst) -> List[Project]:
        return list(Project.objects.filter(assigned_analyst=analyst).order_by('-created_at'))
    
    @staticmethod
    def get_all_projects() -> List[Project]:
        return list(Project.objects.all().order_by('-created_at'))
    
    @staticmethod
    def create_project(client, title: str, description: str, stage: str, 
                      support_type: str, research_area: str, **kwargs) -> Project:
        return Project.objects.create(
            client=client,
            title=title,
            description=description,
            stage=stage,
            support_type=support_type,
            research_area=research_area,
            **kwargs
        )
    
    @staticmethod
    def update_project(project: Project, **kwargs) -> Project:
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        project.save()
        return project
    
    @staticmethod
    def update_status(project: Project, status: str) -> Project:
        project.status = status
        if status == 'completed':
            project.completed_at = timezone.now()
        project.save()
        return project
    
    @staticmethod
    def assign_analyst(project: Project, analyst) -> Project:
        project.assigned_analyst = analyst
        project.status = 'in_progress'
        project.save()
        return project


class MilestoneRepository:
    """Repository for Milestone data access"""
    
    @staticmethod
    def get_by_id(milestone_id) -> Optional[Milestone]:
        try:
            return Milestone.objects.get(id=milestone_id)
        except Milestone.DoesNotExist:
            return None
    
    @staticmethod
    def get_project_milestones(project: Project) -> List[Milestone]:
        return list(project.milestones.all().order_by('created_at'))
    
    @staticmethod
    def get_unfunded_milestones(project: Project) -> List[Milestone]:
        return list(project.milestones.filter(payment_status__in=['unfunded', 'processing']))
    
    @staticmethod
    def get_by_paystack_reference(reference: str) -> List[Milestone]:
        return list(Milestone.objects.filter(paystack_reference=reference, payment_status='processing'))
    
    @staticmethod
    def get_processing_paypal_milestones(project: Project) -> List[Milestone]:
        return list(project.milestones.filter(payment_status='processing', gateway_used='paypal'))
    
    @staticmethod
    def create_milestone(project: Project, title: str, description: str, 
                        amount: Decimal, due_date, delivery_instructions: str = '') -> Milestone:
        return Milestone.objects.create(
            project=project,
            title=title,
            description=description,
            amount=amount,
            due_date=due_date,
            delivery_instructions=delivery_instructions
        )
    
    @staticmethod
    def update_milestone(milestone: Milestone, **kwargs) -> Milestone:
        for key, value in kwargs.items():
            if hasattr(milestone, key):
                setattr(milestone, key, value)
        milestone.save()
        return milestone
    
    @staticmethod
    def update_status(milestone: Milestone, status: str) -> Milestone:
        milestone.status = status
        milestone.save()
        return milestone
    
    @staticmethod
    def update_payment_status(milestone: Milestone, payment_status: str, **kwargs) -> Milestone:
        milestone.payment_status = payment_status
        for key, value in kwargs.items():
            if hasattr(milestone, key):
                setattr(milestone, key, value)
        milestone.save()
        return milestone
    
    @staticmethod
    def bulk_update_payment_status(milestones, payment_status: str, **kwargs):
        milestones.update(payment_status=payment_status, **kwargs)
    
    @staticmethod
    def mark_funded(milestones, gateway: str = None):
        update_fields = {
            'payment_status': 'funded',
            'funded_at': timezone.now()
        }
        milestones.update(**update_fields)


class DeliverableRepository:
    """Repository for Deliverable data access"""
    
    @staticmethod
    def get_project_deliverables(project: Project) -> List[Deliverable]:
        return list(project.deliverables.all())
    
    @staticmethod
    def create_deliverable(project: Project, deliverable_type: str, file, 
                          filename: str, description: str, uploaded_by) -> Deliverable:
        return Deliverable.objects.create(
            project=project,
            deliverable_type=deliverable_type,
            file=file,
            filename=filename,
            description=description,
            uploaded_by=uploaded_by
        )


class ProjectProgressRepository:
    """Repository for ProjectProgress data access"""
    
    @staticmethod
    def get_project_progress(project: Project) -> List[ProjectProgress]:
        return list(ProjectProgress.objects.filter(project=project).order_by('-uploaded_at'))
    
    @staticmethod
    def create_progress(project: Project, file, thumbnail=None) -> ProjectProgress:
        return ProjectProgress.objects.create(
            project=project,
            file=file,
            thumbnail=thumbnail
        )
