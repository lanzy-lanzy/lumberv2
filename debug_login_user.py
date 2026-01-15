import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lumber.settings')
django.setup()

from django.contrib.auth import get_user_model, authenticate
User = get_user_model()

username = 'testuser'
password = 'testpass123'

try:
    user = User.objects.get(username=username)
    print(f"User found: {user.username}")
    print(f"Email: {user.email}")
    print(f"Is Active: {user.is_active}")
    print(f"User Type: {user.user_type}")
    print(f"Role: {user.role}")
    print(f"Password set: {user.has_usable_password()}")
    
    # Check password manually
    auth_user = authenticate(username=username, password=password)
    if auth_user:
        print("Authentication SUCCESS")
    else:
        print("Authentication FAILED")
        
except User.DoesNotExist:
    print(f"User {username} does not exist")
