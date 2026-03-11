# core/middleware.py
from django.contrib.auth.models import AnonymousUser
from core.models import PseudonymousUser

class PseudonymousAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = request.session.get('pseudonymous_user_id')

        if user_id:
            try:
                request.user = PseudonymousUser.objects.get(id=user_id)
            except PseudonymousUser.DoesNotExist:
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()

        return self.get_response(request)
