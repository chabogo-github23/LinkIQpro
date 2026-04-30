"""
Projects Domain Models
- Project: Core project entity
- Milestone: Project milestones with payment tracking
- ProjectFile: File attachments
- Deliverable: Project deliverables
- ProjectProgress: Progress tracking
"""
import uuid
import secrets
import string
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.conf import settings


def generate_project_id():
    """Generate unique project ID in format SIQ-XXXXXX"""
    try:
        prefix = getattr(settings, 'PROJECT_ID_PREFIX', 'SIQ')
    except:
        prefix = 'SIQ'
    
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"{prefix}-{random_part}"


class Project(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('qa', 'QA Review'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('disputed', 'Disputed'),
    ]

    STAGE_CHOICES = [
        ('proposal', 'Proposal'),
        ('data_analysis', 'Data Analysis'),
        ('literature_review', 'Literature Review'),
        ('methodology', 'Methodology'),
        ('full_project', 'Full Project'),
    ]

    SUPPORT_TYPES = [
        ('sample_size', 'Sample Size Calculation'),
        ('analysis_plan', 'Analysis Plan'),
        ('statistical_analysis', 'Statistical Analysis'),
        ('data_cleaning', 'Data Cleaning'),
        ('methodology_review', 'Methodology Review'),
        ('report_writing', 'Report Writing'),
        ('reproducible_notebook', 'Reproducible Notebook'),
        ('other', 'Other'),
    ]

    DEADLINE_RANGE_CHOICES = [
        ('1_5_days', '1 - 5 Days'),
        ('5_10_days', '5 - 10 Days'),
        ('10_20_days', '10 - 20 Days'),
        ('20_30_days', '20 - 30 Days'),
        ('1_2_months', '1 - 2 Months'),
        ('2_3_months', '2 - 3 Months'),
        ('3_plus_months', '3+ Months'),
        ('flexible', 'Flexible / No Rush'),
    ]

    BUDGET_RANGE_CHOICES = [
        ('under_100', 'Under $100'),
        ('100_250', '$100 - $250'),
        ('250_500', '$250 - $500'),
        ('500_1000', '$500 - $1,000'),
        ('1000_2500', '$1,000 - $2,500'),
        ('2500_5000', '$2,500 - $5,000'),
        ('5000_10000', '$5,000 - $10,000'),
        ('10000_plus', '$10,000+'),
        ('discuss', 'Let\'s Discuss'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_id = models.CharField(max_length=20, unique=True, default=generate_project_id)
    client = models.ForeignKey(
        'users.PseudonymousUser', 
        on_delete=models.PROTECT, 
        related_name='projects'
    )
    tenant_admin = models.ForeignKey(
        'users.PseudonymousUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenant_projects'
    )
    assigned_analyst = models.ForeignKey(
        'users.PseudonymousUser', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='assigned_projects'
    )

    title = models.CharField(max_length=500)
    description = models.TextField()
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    support_type = models.CharField(max_length=50, choices=SUPPORT_TYPES)
    research_area = models.CharField(max_length=255)

    sample_size = models.IntegerField(null=True, blank=True)
    preferred_methods = models.TextField(null=True, blank=True)
    
    deadline = models.DateField(null=True, blank=True)
    deadline_range = models.CharField(
        max_length=20, 
        choices=DEADLINE_RANGE_CHOICES, 
        null=True, 
        blank=True,
        help_text='Expected timeline for project completion'
    )
    
    budget_range = models.CharField(
        max_length=20, 
        choices=BUDGET_RANGE_CHOICES, 
        null=True, 
        blank=True,
        help_text='Expected budget range for the project'
    )
    
    attachment = models.FileField(
        upload_to='project_attachments/%Y/%m/%d/', 
        null=True, 
        blank=True,
        help_text='Optional document with additional project details'
    )
    attachment_filename = models.CharField(max_length=500, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
  
    confirms_lawful_use = models.BooleanField(default=False)
    confirms_data_rights = models.BooleanField(default=False)
    irb_approval_provided = models.BooleanField(default=False)
 
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sub_admin_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    released_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'core_project'
        indexes = [
            models.Index(fields=['project_id']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.project_id} - {self.title}"

    def get_deadline_range_display_text(self):
        """Get human-readable deadline range"""
        if self.deadline_range:
            return dict(self.DEADLINE_RANGE_CHOICES).get(self.deadline_range, self.deadline_range)
        return None

    def get_budget_range_display_text(self):
        """Get human-readable budget range"""
        if self.budget_range:
            return dict(self.BUDGET_RANGE_CHOICES).get(self.budget_range, self.budget_range)
        return None

    def save(self, *args, **kwargs):
        """Update calculated price fields when saving"""
        if self.pk:
            milestones = self.milestones.all()
            self.total_price = sum(milestone.amount for milestone in milestones)
            self.paid_amount = sum(milestone.amount for milestone in milestones 
                                 if milestone.payment_status in ['funded', 'released'])
            self.released_amount = sum(milestone.amount for milestone in milestones 
                                     if milestone.payment_status == 'released')
        if self.tenant_admin and self.total_price:
            self.sub_admin_fee = self.total_price * Decimal('0.02')
        else:
            self.sub_admin_fee = 0
        
        super().save(*args, **kwargs)

    @property
    def payment_status(self):
        """Overall project payment status based on milestones"""
        milestones = self.milestones.all()
        if not milestones:
            return 'no_milestones'
        
        statuses = [m.payment_status for m in milestones]
        
        if all(status == 'released' for status in statuses):
            return 'fully_released'
        elif any(status == 'released' for status in statuses):
            return 'partially_released'
        elif all(status == 'funded' for status in statuses):
            return 'fully_funded'
        elif any(status == 'funded' for status in statuses):
            return 'partially_funded'
        else:
            return 'unfunded'

    @property
    def progress_percentage(self):
        """Calculate project completion percentage based on milestones"""
        milestones = self.milestones.all()
        if not milestones:
            return 0
        
        completed = sum(1 for m in milestones if m.status == 'approved')
        return int((completed / len(milestones)) * 100)


class Milestone(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed - Ready for Review'),
        ('approved', 'Approved - Payment Ready'),
        ('rejected', 'Rejected - Needs Revision'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('unfunded', 'Unfunded'),
        ('processing', 'Processing Payment'),
        ('funded', 'Funded - Payment Received'),
        ('released', 'Released to Admin'),
        ('refunded', 'Refunded to Client'),
        ('failed', 'Payment Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0.01)]
    )
    due_date = models.DateField()
    delivery_instructions = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unfunded')
    
    # Payment gateway tracking
    gateway_used = models.CharField(
        max_length=20, 
        choices=[('paypal', 'PayPal'), ('paystack', 'PayStack')], 
        blank=True, null=True
    )
    
    # PayPal specific fields
    paypal_order_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_auth_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Paystack specific fields
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    paystack_currency = models.CharField(max_length=10, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    funded_at = models.DateTimeField(blank=True, null=True)
    released_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['created_at']
        db_table = 'core_milestone'
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"{self.project.project_id} - {self.title} (${self.amount})"
    
    def save(self, *args, **kwargs):
        """Handle status transitions and timestamps"""
        if self.pk:
            old_instance = Milestone.objects.filter(pk=self.pk).first()
            if old_instance:
                if old_instance.payment_status != 'funded' and self.payment_status == 'funded':
                    self.funded_at = timezone.now()
                
                if old_instance.payment_status != 'released' and self.payment_status == 'released':
                    self.released_at = timezone.now()
                    
                if old_instance.status != 'approved' and self.status == 'approved':
                    self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
        if self.project:
            self.project.save()
    
    @property
    def is_funded(self):
        return self.payment_status in ['funded', 'released']
    
    @property
    def is_releasable(self):
        """Check if payment can be released (work approved and payment funded)"""
        return self.status == 'approved' and self.payment_status == 'funded'
    
    @property
    def is_overdue(self):
        """Check if milestone is past due date and not completed"""
        if self.due_date and self.status not in ['completed', 'approved']:
            return self.due_date < timezone.now().date()
        return False


class ProjectFile(models.Model):
    """Files uploaded for a project"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='project_files/%Y/%m/%d/')
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, null=True, blank=True, related_name='files')
    filename = models.CharField(max_length=500)
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        'users.PseudonymousUser', 
        on_delete=models.SET_NULL, 
        null=True
    )
    
    class Meta:
        ordering = ['-uploaded_at']
        db_table = 'core_projectfile'
    
    def __str__(self):
        return f"{self.project.project_id} - {self.filename}"


class Deliverable(models.Model):
    """Project deliverables"""
    DELIVERABLE_TYPES = [
        ('report', 'PDF Report'),
        ('notebook', 'Reproducible Notebook'),
        ('code', 'Code Bundle'),
        ('data_log', 'Data Processing Log'),
        ('sow', 'Statement of Work'),
        ('qa_report', 'QA Report'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='deliverables')
    deliverable_type = models.CharField(max_length=50, choices=DELIVERABLE_TYPES)
    file = models.FileField(upload_to='deliverables/%Y/%m/%d/')
    filename = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        'users.PseudonymousUser', 
        on_delete=models.SET_NULL, 
        null=True
    )
    
    class Meta:
        ordering = ['-uploaded_at']
        db_table = 'core_deliverable'
    
    def __str__(self):
        return f"{self.project.project_id} - {self.get_deliverable_type_display()}"


class ProjectProgress(models.Model):
    """Progress tracking files for projects"""
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="progress_updates"
    )
    file = models.FileField(upload_to="project_progress/")
    thumbnail = models.ImageField(upload_to="project_progress/thumbnails/", blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_projectprogress'

    def __str__(self):
        return f"Progress for {self.project.project_id} - {self.uploaded_at:%Y-%m-%d}"

    @property
    def thumbnail_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        return None
