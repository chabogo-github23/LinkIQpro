from django.core.management.base import BaseCommand, CommandError
from core.models import PseudonymousUser

class Command(BaseCommand):
    help = 'Delete a pseudonymous user by alias or email'

    def add_arguments(self, parser):
        parser.add_argument('--alias', type=str, help='Alias of the user to delete')
        parser.add_argument('--email', type=str, help='Email of the user to delete')

    def handle(self, *args, **options):
        alias = options.get('alias')
        email = options.get('email')

        if not alias and not email:
            raise CommandError('Please provide either --alias or --email.')

        # Delete by alias or email
        qs = PseudonymousUser.objects.filter(alias=alias) if alias else PseudonymousUser.objects.filter(email=email)
        if not qs.exists():
            raise CommandError('User not found.')

        count, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Successfully deleted {count} user(s).'))
