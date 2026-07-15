# core/urls.py
"""
Core URL Configuration
Maintains backward compatibility while routing to refactored domain views
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # --- Main views ---
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('projects/', views.projects_redirect, name='projects'),
    path('login/', views.login_placeholder, name='login'),
    path('auth/register/', views.register, name='register'),
    path('auth/request-magic-link/', views.request_magic_link, name='request_magic_link'),
    path('auth/verify-magic-link/', views.verify_magic_link, name='verify_magic_link'),
    path('logout/', views.logout_view, name='logout'),
    # Password reset
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('reset-password/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # Dashboards
    path('dashboard/client/', views.client_dashboard, name='client_dashboard'),
    path('dashboard/analyst/', views.analyst_dashboard, name='analyst_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/sub-admin/', views.sub_admin_dashboard, name='sub_admin_dashboard'),
    path('dashboard/sub-admin/activities/', views.sub_admin_activities, name='sub_admin_activities'),
    path('dashboard/sub-admin/analysts/', views.sub_admin_analyst_list, name='sub_admin_analyst_list'),
    path('dashboard/sub-admin/analysts/create/', views.sub_admin_create_analyst, name='sub_admin_create_analyst'),
    path('dashboard/sub-admin/analysts/<uuid:user_id>/', views.sub_admin_analyst_detail, name='sub_admin_analyst_detail'),
    path('dashboard/sub-admin/analysts/<uuid:user_id>/edit/', views.sub_admin_edit_analyst, name='sub_admin_edit_analyst'),
    path('dashboard/sub-admin/projects/', views.sub_admin_project_list, name='sub_admin_project_list'),
    path('dashboard/sub-admin/projects/<str:project_id>/', views.sub_admin_project_manage, name='sub_admin_project_manage'),

    # Project submission
    path('project/submit/', views.submit_project, name='submit_project'),

    # --- Admin project routes ---
    path('dashboard/admin/project/<str:project_id>/', views.project_triage, name='project_triage'),
    path('project/<str:project_id>/admin/review/', views.admin_project_review, name='admin_project_review'),
    path('project/<str:project_id>/admin/assign-analyst/', views.admin_assign_analyst, name='admin_assign_analyst'),
    path('project/<str:project_id>/admin/review-deliverable/', views.admin_review_deliverable, name='admin_review_deliverable'),
    path('project/<str:project_id>/admin/deliver-to-client/', views.admin_deliver_to_client, name='admin_deliver_to_client'),
    path('dashboard/admin/project/<str:project_id>/progress/upload/', views.admin_upload_progress, name='admin_upload_progress'),
    #path('progress/<int:progress_id>/view/', views.view_progress_pdf, name='view_progress_pdf'),
    path('progress/<int:progress_id>/view/', 
     views.view_progress_pdf, 
     name='view_progress_pdf'),
    
    # User management
    path('dashboard/admin/users/', views.admin_user_management, name='admin_user_management'),
    path('dashboard/admin/users/create/', views.admin_create_user, name='admin_create_user'),
    path('dashboard/admin/users/<uuid:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('dashboard/admin/users/<uuid:user_id>/edit/', views.admin_edit_user, name='admin_edit_user'),
    path('dashboard/admin/users/<uuid:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),

    # --- General project routes ---
    path('project/<str:project_id>/', views.project_detail, name='project_detail'),
    path('dashboard/analyst/project/<str:project_id>/', views.analyst_project_detail, name='analyst_project_detail'),
    path('dashboard/analyst/project/<str:project_id>/upload/', views.analyst_upload_deliverable, name='analyst_upload_deliverable'),
    path('dashboard/analyst/project/<str:project_id>/submit/', views.analyst_submit_work, name='analyst_submit_work'),
    path('dashboard/analyst/project/<str:project_id>/messages/', views.analyst_view_messages, name='analyst_view_messages'),
    path('project/<str:project_id>/chat/', views.project_chat, name='project_chat'),
    path('project/<str:project_id>/propose-price/', views.propose_price, name='propose_price'),
    path('project/<str:project_id>/agree-terms/', views.agree_terms, name='agree_terms'),

    # Milestone routes
    path('project/<str:project_id>/milestones/create/', views.create_milestone, name='create_milestone'),
    path('milestone/<uuid:milestone_id>/update-status/', views.update_milestone_status, name='update_milestone_status'),
    path('milestone/<uuid:milestone_id>/approve/', views.approve_milestone, name='approve_milestone'),
    path('milestone/<uuid:milestone_id>/release-payment/', views.release_milestone_payment, name='release_milestone_payment'),
    
    # Milestone payments
    path('project/<str:project_id>/milestone-payment/', views.milestone_payment_page, name='milestone_payment'),
    path('project/<str:project_id>/create-milestone-payment/', views.create_milestone_payment, name='create_milestone_payment'),
    path('project/<str:project_id>/validate-payment-email/', views.validate_payment_email, name='validate_payment_email'),
    path('project/<str:project_id>/payment/success/', views.payment_success, name='payment_success'),
    path('project/<str:project_id>/payment/cancel/', views.payment_cancel, name='payment_cancel'),
]
