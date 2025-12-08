# 🔐 Authentication System - Code Reference

## File Structure

```
lumber/
├── app_authentication/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── views.py          ← NEW: Login/Register/Logout
│   ├── urls.py           ← NEW: URL routing
│   └── migrations/
│
├── core/
│   ├── models.py         ← UPDATED: CustomUser with roles
│   ├── views.py          ← UPDATED: home() view with auth
│   ├── urls.py           ← Links to home view
│   ├── serializers.py
│   └── migrations/
│
├── lumber/
│   ├── settings.py       ← AUTH_USER_MODEL = 'core.CustomUser'
│   ├── urls.py           ← UPDATED: auth routes + core URLs
│   ├── wsgi.py
│   ├── asgi.py
│   └── __init__.py
│
└── templates/
    ├── authentication/
    │   ├── login.html     ← NEW: Login form
    │   └── register.html  ← NEW: Registration form
    ├── landing.html       ← User lands here after login
    └── [other templates]
```

---

## Core Components

### 1. User Model (core/models.py)

```python
class CustomUser(AbstractUser):
    """Extended User model with role-based access control"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('inventory_manager', 'Inventory Manager'),
        ('cashier', 'Cashier'),
        ('warehouse_staff', 'Warehouse Staff'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='warehouse_staff'
    )
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Helper methods
    def is_admin(self):
        return self.role == 'admin'
    
    def is_inventory_manager(self):
        return self.role == 'inventory_manager'
    
    def is_cashier(self):
        return self.role == 'cashier'
    
    def is_warehouse_staff(self):
        return self.role == 'warehouse_staff'
```

---

### 2. Authentication Views (app_authentication/views.py)

#### Login View
```python
@require_http_methods(["GET", "POST"])
def login_view(request):
    """User login view"""
    # Already authenticated? Redirect to home
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'authentication/login.html')
```

#### Register View
```python
@require_http_methods(["GET", "POST"])
def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        password_confirm = request.POST.get('password_confirm', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        role = request.POST.get('role', 'warehouse_staff').strip()
        
        # Validation
        errors = []
        if not first_name:
            errors.append('First name is required.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != password_confirm:
            errors.append('Passwords do not match.')
        if CustomUser.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        
        if errors:
            return render(request, 'authentication/register.html', {
                'errors': errors,
                'form_data': {...}
            })
        
        # Create user
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role=role,
        )
        
        return redirect('login')
    
    return render(request, 'authentication/register.html', {
        'role_choices': ROLE_CHOICES
    })
```

#### Logout View
```python
@login_required
@require_http_methods(["POST"])
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')
```

---

### 3. URL Routing (app_authentication/urls.py)

```python
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
```

---

### 4. Main URLs (lumber/urls.py)

```python
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# ... router setup ...

urlpatterns = [
    path('', include('core.urls')),                 # Home at /
    path('auth/', include('app_authentication.urls')),  # Auth at /auth/
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
]
```

---

### 5. Home View (core/views.py)

```python
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def home(request):
    """Landing page - main entry point"""
    # Redirect to login if not authenticated
    if not request.user.is_authenticated:
        return redirect('login')
    
    context = {
        'user': request.user,
    }
    return render(request, 'landing.html', context)
```

---

## Template Examples

### Login Form (templates/authentication/login.html)

```html
<form method="POST" class="space-y-6">
    {% csrf_token %}
    
    <div>
        <label for="username" class="block text-sm font-medium">Username</label>
        <input
            type="text"
            id="username"
            name="username"
            required
            class="w-full px-4 py-2 rounded-lg border focus:ring-2 focus:ring-amber-600"
        >
    </div>
    
    <div>
        <label for="password" class="block text-sm font-medium">Password</label>
        <input
            type="password"
            id="password"
            name="password"
            required
            class="w-full px-4 py-2 rounded-lg border focus:ring-2 focus:ring-amber-600"
        >
    </div>
    
    <button type="submit" class="w-full py-2 bg-amber-600 text-white rounded-lg">
        Sign In
    </button>
</form>
```

### Register Form with Role Selection

```html
<select name="role" required class="w-full px-4 py-2 rounded-lg border">
    {% for value, label in role_choices %}
        <option value="{{ value }}">{{ label }}</option>
    {% endfor %}
</select>
```

### Using Auth in Templates

```html
<!-- Check authentication -->
{% if user.is_authenticated %}
    <p>Hello, {{ user.get_full_name }}!</p>
{% else %}
    <p><a href="{% url 'login' %}">Login</a></p>
{% endif %}

<!-- Check role -->
{% if user.role == 'admin' %}
    <a href="/admin/">Admin Panel</a>
{% endif %}

<!-- Logout form -->
<form method="POST" action="{% url 'logout' %}">
    {% csrf_token %}
    <button type="submit">Logout</button>
</form>
```

---

## API Usage Examples

### Login (Session-based)
```bash
curl -X POST http://localhost:8000/api-auth/login/ \
  -d "username=johndoe&password=MyPassword123"
```

### Get Current User
```bash
curl http://localhost:8000/api/users/me/ \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

### Filter Users by Role
```bash
curl http://localhost:8000/api/users/by_role/?role=admin \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

---

## Settings Configuration (lumber/settings.py)

```python
# User model
AUTH_USER_MODEL = 'core.CustomUser'

# Installed apps includes
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'core',
    'app_authentication',
    # ...
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}
```

---

## Database Queries

### Get user by username
```python
from core.models import CustomUser

user = CustomUser.objects.get(username='johndoe')
```

### Filter by role
```python
admins = CustomUser.objects.filter(role='admin')
managers = CustomUser.objects.filter(role='inventory_manager')
```

### Check user properties
```python
if user.is_admin():
    # admin logic
    
if user.is_active:
    # user is active
    
user.created_at  # registration date
user.updated_at  # last update
```

---

## Validation Logic

### Password Validation
```python
# Minimum 8 characters
if len(password) < 8:
    errors.append('Password must be at least 8 characters long.')

# Password match
if password != password_confirm:
    errors.append('Passwords do not match.')
```

### Email Validation
```python
# Built-in EmailField validation via Django forms
# Or manual check:
if '@' not in email or '.' not in email.split('@')[1]:
    errors.append('Invalid email address.')
```

### Username Validation
```python
# Uniqueness check
if CustomUser.objects.filter(username=username).exists():
    errors.append('Username already exists.')

# Length check (Django built-in: max 150 chars)
if len(username) > 150:
    errors.append('Username too long.')
```

### Phone Number Validation
```python
# Regex: optional +, followed by 9-15 digits
import re
if phone_number and not re.match(r'^\+?1?\d{9,15}$', phone_number):
    errors.append('Invalid phone number.')
```

---

## Decorators Used

```python
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

# Require authentication
@login_required
def protected_view(request):
    pass

# Restrict HTTP methods
@require_http_methods(["GET", "POST"])
def form_view(request):
    pass

# Secure logout (POST only)
@login_required
@require_http_methods(["POST"])
def logout_view(request):
    pass
```

---

## Error Handling

### Authentication Errors
```python
user = authenticate(request, username=username, password=password)
if user is None:
    messages.error(request, 'Invalid username or password.')
```

### Validation Errors
```python
errors = []
if not username:
    errors.append('Username is required.')
if errors:
    context['errors'] = errors
    return render(request, 'template.html', context)
```

### Database Errors
```python
try:
    user = CustomUser.objects.create_user(...)
except IntegrityError:
    messages.error(request, 'User creation failed.')
```

---

## Best Practices Implemented

✅ **Security**
- Passwords hashed with Django's default hasher
- CSRF token required on all forms
- SQL injection prevention via ORM
- XSS protection in templates

✅ **Code Quality**
- Separate views for login, register, logout
- Clear separation of concerns
- Input validation on both client and server
- Error messages for user feedback

✅ **User Experience**
- Responsive design with Tailwind CSS
- Clear error messages
- Form validation feedback
- Smooth redirects after auth

✅ **Maintainability**
- Well-documented code
- Following Django conventions
- DRY principle (Don't Repeat Yourself)
- Easy to extend

---

## Common Customizations

### Change Default Role
```python
# In models.py
role = models.CharField(
    max_length=20,
    choices=ROLE_CHOICES,
    default='admin'  # Changed from 'warehouse_staff'
)
```

### Add More Roles
```python
ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('manager', 'Manager'),
    ('supervisor', 'Supervisor'),
    ('staff', 'Staff'),
]
```

### Add More User Fields
```python
# In views.py register_view()
department = request.POST.get('department', '').strip()

# In CustomUser model
department = models.CharField(max_length=100, blank=True)
```

### Change Password Requirements
```python
# In views.py
if len(password) < 12:  # Changed from 8
    errors.append('Password must be at least 12 characters.')
```

---

## Testing

### Manual Test Script
```python
# In Django shell
from core.models import CustomUser

# Create user
user = CustomUser.objects.create_user(
    username='testuser',
    email='test@example.com',
    password='TestPassword123',
    first_name='Test',
    last_name='User',
    role='inventory_manager'
)

# Check user
print(user.is_inventory_manager())  # True
print(user.is_admin())               # False

# Test authentication
from django.contrib.auth import authenticate
user = authenticate(username='testuser', password='TestPassword123')
print(user.get_full_name())          # Test User
```

---

**Status:** Complete & Ready to Use  
**Last Updated:** December 2024
