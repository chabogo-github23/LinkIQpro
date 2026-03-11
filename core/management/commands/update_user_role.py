"""
Management command to update a user's role.
Usage:
    python manage.py update_user_role --alias admin_shadow --role admin
    python manage.py update_user_role --alias analyst_john --role analyst
    python manage.py update_user_role --alias client_alice --role client
"""

from django.core.management.base import BaseCommand, CommandError
from core.models import PseudonymousUser


class Command(BaseCommand):
    help = 'Update a user\'s role'

    def add_arguments(self, parser):
        parser.add_argument(
            '--alias',
            type=str,
            required=True,
            help='User alias to update'
        )
        parser.add_argument(
            '--role',
            type=str,
            choices=['client', 'admin', 'analyst'],
            required=True,
            help='New role for the user'
        )

    def handle(self, *args, **options):
        alias = options['alias'].strip()
        new_role = options['role'].strip()

        try:
            user = PseudonymousUser.objects.get(alias=alias)
        except PseudonymousUser.DoesNotExist:
            raise CommandError(f'User with alias "{alias}" not found')

        # Get old role
        if user.is_admin:
            old_role = 'admin'
        elif user.is_analyst:
            old_role = 'analyst'
        else:
            old_role = 'client'

        # Update role
        user.is_admin = (new_role == 'admin')
        user.is_analyst = (new_role == 'analyst')
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Updated {alias}: {old_role.upper()} → {new_role.upper()}'
            )
        )
