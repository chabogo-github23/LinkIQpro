"""
Payments Domain Views
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.conf import settings

from apps.projects.models import Project, Milestone
from apps.users.decorators import (
    pseudonymous_user_required as require_auth,
    admin_required as require_admin,
    get_client_ip
)
from apps.audit.services import AuditService
from .services import MilestonePaymentService
from .utils import convert_usd_to_currency, format_currency_amount


@require_auth
def milestone_payment_page(request, project_id):
    """Payment page for milestones"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if not request.user or project.client_id != request.user.id:
        return render(request, "core/access_denied.html", status=403)

    milestones = project.milestones.filter(payment_status__in=['unfunded', 'processing'])
    
    return render(request, "core/milestone_payment.html", {
        "project": project,
        "milestones": milestones,
        "paypal_client_id": settings.PAYPAL_CLIENT_ID,
        "milestones_ids": [str(m.id) for m in milestones],
        "total_amount": sum(m.amount for m in milestones)
    })


@require_auth
@require_POST
def create_milestone_payment(request, project_id):
    """Create payment for milestones"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if project.client_id != request.user.id:
        return render(request, "core/access_denied.html", status=403)

    try:
        data = json.loads(request.body)
        milestone_ids = data.get("milestone_ids", [])
        gateway = data.get("gateway")
        user_email = data.get("user_email")
        currency = data.get("currency", "USD")
        
        if gateway not in ['paypal', 'paystack']:
            return JsonResponse({"error": "Invalid payment gateway"}, status=400)
        
        # Build callback URL
        callback_url = request.build_absolute_uri(
            f"/project/{project.project_id}/payment/success/?method={gateway}"
        )
        
        service = MilestonePaymentService()
        result = service.initiate_payment(
            project=project,
            milestone_ids=milestone_ids,
            gateway_name=gateway,
            callback_url=callback_url,
            user_email=user_email,
            currency=currency
        )
        
        if result.success:
            response_data = {
                "success": True,
                "approval_url": result.authorization_url,
                "authorization_url": result.authorization_url,
                "paypal_order_id": result.order_id,
                "reference": result.reference,
                "amount": float(result.total_amount),
                "milestone_count": result.milestone_count,
                "currency": result.currency,
            }
            
            # Add converted amount info for Paystack payments
            if gateway == 'paystack' and result.converted_amount:
                response_data["converted_amount"] = result.converted_amount
                response_data["converted_display"] = format_currency_amount(
                    result.converted_amount, result.currency
                )
            
            return JsonResponse(response_data)
        
        return JsonResponse({"error": result.error}, status=400)
    
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_auth
@require_http_methods(["POST"])
def validate_payment_email(request, project_id):
    """Validate email for Paystack payment"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if project.client_id != request.user.id:
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        data = json.loads(request.body)
        email = data.get("email", "").strip()
        
        if not email:
            return JsonResponse({"valid": False, "error": "Email is required"})
        
        has_stored_hash = bool(request.user.email_hash)
        
        if has_stored_hash:
            matches = request.user.check_email(email)
            return JsonResponse({
                "valid": True,
                "has_stored_hash": True,
                "matches_hash": matches,
                "warning": None if matches else "The email you entered does not match your registered email."
            })
        else:
            return JsonResponse({
                "valid": True,
                "has_stored_hash": False,
                "matches_hash": None,
                "warning": None
            })
            
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@require_auth
def payment_success(request, project_id):
    """Handle payment success callback"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if project.client_id != request.user.id:
        return render(request, "core/access_denied.html", status=403)
    
    method = request.GET.get("method", "").lower()
    paypal_order_id = request.GET.get("token")
    paystack_reference = request.GET.get("reference")
    
    service = MilestonePaymentService()
    
    if method == "paystack" or paystack_reference:
        success, message, milestones = service.verify_paystack_payment(project, paystack_reference)
        
        if success:
            AuditService.log_from_request('paystack_payment_success', request, project,
                details={"reference": paystack_reference, "milestone_count": len(milestones)})
            messages.success(request, "Paystack payment completed successfully!")
            return render(request, "core/payment_success.html", {"project": project, "milestones": milestones})
        else:
            AuditService.log_from_request('paystack_payment_failed', request, project,
                details={"reference": paystack_reference, "reason": message})
            messages.error(request, f"Payment failed: {message}")
            return render(request, "core/payment_failed.html", {"project": project, "error": message, "can_retry": True})
    
    elif method == "paypal" or paypal_order_id:
        success, message, milestones, auth_id = service.verify_paypal_payment(project, paypal_order_id)
        
        if success:
            AuditService.log_from_request('paypal_funds_held', request, project,
                details={"paypal_order_id": paypal_order_id, "paypal_auth_id": auth_id, "milestone_count": len(milestones)})
            messages.success(request, f"Funds held in escrow for {len(milestones)} milestones")
            return render(request, "core/payment_success.html", {"project": project, "milestones": milestones})
        else:
            AuditService.log_from_request('paypal_authorization_failed', request, project,
                details={"error": message, "order_id": paypal_order_id})
            messages.error(request, "PayPal authorization failed. Please try again.")
            return render(request, "core/payment_failed.html", {"project": project, "error": message, "can_retry": True})
    
    messages.error(request, "Invalid payment callback. Please try again.")
    return redirect('core:milestone_payment', project_id=project.project_id)


@require_auth
def payment_cancel(request, project_id):
    """Handle payment cancellation"""
    project = get_object_or_404(Project, project_id=project_id)
    
    if project.client_id != request.user.id:
        return render(request, "core/access_denied.html", status=403)
    
    service = MilestonePaymentService()
    count = service.cancel_payment(project)
    
    AuditService.log_from_request('payment_cancelled', request, project,
        details={"milestone_count": count})
    
    messages.warning(request, "Payment was cancelled. You can try again when ready.")
    return render(request, "core/payment_cancel.html", {"project": project})


@require_admin
@require_POST
def release_milestone_payment(request, milestone_id):
    """Release PayPal payment for approved milestone"""
    milestone = get_object_or_404(Milestone, id=milestone_id)

    if not milestone.is_releasable:
        messages.error(request, "Milestone not ready for release.")
        return redirect('core:project_triage', project_id=milestone.project.project_id)

    service = MilestonePaymentService()
    
    if milestone.gateway_used == 'paypal':
        success, message = service.release_paypal_payment(milestone)
        
        if success:
            AuditService.log_from_request('paypal_payment_captured', request, milestone.project,
                milestone=milestone, details={'title': milestone.title, 'amount': float(milestone.amount)})
            messages.success(request, message)
        else:
            messages.error(request, f"Release failed: {message}")
    
    elif milestone.gateway_used == 'paystack':
        # Paystack payments are auto-released on approval
        milestone.payment_status = 'released'
        milestone.save()
        
        AuditService.log_from_request('paystack_payment_released', request, milestone.project,
            milestone=milestone, details={'title': milestone.title, 'amount': float(milestone.amount)})
        messages.success(request, f'Payment marked as released for "{milestone.title}"')
    
    else:
        messages.error(request, "Unknown payment gateway.")

    return redirect('core:project_triage', project_id=milestone.project.project_id)
