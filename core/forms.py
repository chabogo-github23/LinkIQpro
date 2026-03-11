from django import forms
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
from .models import PseudonymousUser
from .tokens import token_generator

class CustomPasswordResetForm(forms.Form):
    alias = forms.CharField(label="Username / Alias")
    email = forms.EmailField(label="Send reset link to this email")

    def clean_alias(self):
        alias = self.cleaned_data['alias']
        try:
            self.user = PseudonymousUser.objects.get(alias=alias)
        except PseudonymousUser.DoesNotExist:
            raise forms.ValidationError("Unknown alias.")
        return alias

    def save(self, request):
        user = self.user
        email = self.cleaned_data["email"]

        uid = urlsafe_base64_encode(force_bytes(str(user.pk)))
        token = token_generator.make_token(user)

        current_site = get_current_site(request)
        context = {
            'email': email,
            'domain': current_site.domain,
            'site_name': current_site.name,
            'uid': uid,
            'user': user,
            'token': token,
            'protocol': 'https' if request.is_secure() else 'http',
        }

        send_mail(
            subject="Password Reset Request",
            message=f"Use the link to reset your password: {context['protocol']}://{context['domain']}/reset-password/{uid}/{token}/",
            from_email=None,
            recipient_list=[email],
        )


class CustomSetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        if data.get('new_password') != data.get('confirm_password'):
            raise forms.ValidationError("Passwords do not match.")
        return data
class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = PseudonymousUser
        fields = ['alias', 'email', 'password', 'is_admin', 'is_analyst', 'is_active']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if user.is_admin:
            user.is_staff = True
            user.is_superuser = True
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    class Meta:
        model = PseudonymousUser
        fields = ['alias', 'email', 'is_admin', 'is_analyst', 'is_active']
