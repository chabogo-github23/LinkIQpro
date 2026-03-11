"""
Management command to list all pseudonymous users.
Usage:
    python manage.py list_users
    python manage.py list_users --role admin
    python manage.py list_users --role analyst
"""

from django.core.management.base import BaseCommand
from core.models import PseudonymousUser


class Command(BaseCommand):
    help = 'List all pseudonymous users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            choices=['client', 'admin', 'analyst'],
            help='Filter by role'
        )

    def handle(self, *args, **options):
        role_filter = options.get('role')

        # Build query
        users = PseudonymousUser.objects.all().order_by('-created_at')

        if role_filter == 'admin':
            users = users.filter(is_admin=True)
        elif role_filter == 'analyst':
            users = users.filter(is_analyst=True)
        elif role_filter == 'client':
            users = users.filter(is_admin=False, is_analyst=False)

        if not users.exists():
            self.stdout.write(self.style.WARNING('No users found'))
            return

        # Display header
        self.stdout.write('\n' + '=' * 100)
        self.stdout.write(
            f'{"ALIAS":<25} {"EMAIL":<30} {"ROLE":<15} {"CREATED":<20} {"LAST LOGIN":<20}'
        )
        self.stdout.write('=' * 100)

        # Display users
        for user in users:
            if user.is_admin:
                role = 'ADMIN'
            elif user.is_analyst:
                role = 'ANALYST'
            else:
                role = 'CLIENT'

            last_login = user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never'
            created = user.created_at.strftime('%Y-%m-%d %H:%M')

            self.stdout.write(
                f'{user.alias:<25} {user.email or "N/A":<30} {role:<15} {created:<20} {last_login:<20}'
            )

        self.stdout.write('=' * 100 + '\n')
        self.stdout.write(self.style.SUCCESS(f'Total users: {users.count()}'))
