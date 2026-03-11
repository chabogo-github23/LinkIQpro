"""
Management command to create pseudonymous users with hashed passwords.
Usage:
    python manage.py create_user --alias admin_shadow --email admin@shadowiq.com --role admin --password mysecret
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from core.models import PseudonymousUser
import secrets


class Command(BaseCommand):
    help = 'Create a pseudonymous user with a specific role and hashed password'

    def add_arguments(self, parser):
        parser.add_argument('--alias', type=str, required=True, help='Unique alias for the user')
        parser.add_argument('--email', type=str, required=True, help='Email address for the user')
        parser.add_argument(
            '--role',
            type=str,
            choices=['client', 'admin', 'analyst'],
            default='client',
            help='User role (default: client)'
        )
        parser.add_argument('--password', type=str, required=True, help='Password for the user')

    def handle(self, *args, **options):
        alias = options['alias'].strip()
        email = options['email'].strip()
        role = options['role'].strip()
        password = options['password'].strip()

        if not alias or len(alias) < 3:
            raise CommandError('Alias must be at least 3 characters long')

        if '@' not in email:
            raise CommandError('Invalid email address')

        if len(password) < 6:
            raise CommandError('Password must be at least 6 characters long')

        if PseudonymousUser.objects.filter(alias=alias).exists():
            raise CommandError(f'User with alias "{alias}" already exists')

        if PseudonymousUser.objects.filter(email=email).exists():
            raise CommandError(f'User with email "{email}" already exists')

        try:
            user = PseudonymousUser.objects.create(
                alias=alias,
                email=email,
                is_admin=(role == 'admin'),
                is_analyst=(role == 'analyst'),
                magic_token=secrets.token_urlsafe(32),
                magic_token_expires=timezone.now() + timezone.timedelta(hours=24)
            )
            user.set_password(password)  # ✅ Securely hash and save the password

            self.stdout.write(self.style.SUCCESS(f'✓ Successfully created {role.upper()} user: {alias}'))
            self.stdout.write(f'  Email: {email}')
            self.stdout.write(f'  Password: [hashed securely]')
            self.stdout.write(f'  ID: {user.id}')
            self.stdout.write(f'  Created: {user.created_at}')

        except Exception as e:
            raise CommandError(f'Failed to create user: {str(e)}')
