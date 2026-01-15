from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import CustomerProfile
from django.utils.crypto import get_random_string

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a new customer user with credentials'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for login')
        parser.add_argument('email', type=str, help='Email address')
        parser.add_argument('--password', type=str, help='Password (optional, will auto-generate if not provided)')
        parser.add_argument('--first-name', type=str, default='', help='First name')
        parser.add_argument('--last-name', type=str, default='', help='Last name')
        parser.add_argument('--phone', type=str, default='', help='Phone number')
        parser.add_argument('--no-approve', action='store_true', help='Do not automatically approve the user')

    def handle(self, *args, **options):
        username = options['username'].strip()
        email = options['email'].strip()
        password = options['password'].strip() if options['password'] else None
        first_name = options['first_name'].strip()
        last_name = options['last_name'].strip()
        phone = options['phone'].strip()
        auto_approve = not options['no_approve']

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User with username "{username}" already exists.'))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'User with email "{email}" already exists.'))
            return

        if not password:
            password = get_random_string(10)

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
                user_type='customer',
                role=None,
                is_approved=auto_approve
            )

            # Create CustomerProfile
            CustomerProfile.objects.create(
                user=user,
                address='', # Can be updated later
                is_senior=False,
                is_pwd=False
            )

            self.stdout.write(self.style.SUCCESS(f'Successfully created customer user: {username}'))
            self.stdout.write(f'Email: {email}')
            self.stdout.write(f'Password: {password}')
            if auto_approve:
                self.stdout.write(self.style.SUCCESS('User is APPROVED and can log in immediately.'))
            else:
                self.stdout.write(self.style.WARNING('User is PENDING approval.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating user: {str(e)}'))
