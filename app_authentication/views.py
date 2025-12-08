from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import IntegrityError
from core.models import CustomUser, ROLE_CHOICES


@require_http_methods(["GET", "POST"])
def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
            return render(request, 'authentication/login.html')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Get next URL from request, or redirect based on user role
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            # All authenticated users go to dashboard (role-based views handled there)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
            return render(request, 'authentication/login.html', {'username': username})
    
    context = {
        'page_title': 'Login',
    }
    return render(request, 'authentication/login.html', context)


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
        if not last_name:
            errors.append('Last name is required.')
        if not email:
            errors.append('Email is required.')
        if not username:
            errors.append('Username is required.')
        if not password:
            errors.append('Password is required.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        if password != password_confirm:
            errors.append('Passwords do not match.')
        if role not in [choice[0] for choice in ROLE_CHOICES]:
            errors.append('Invalid role selected.')
        
        # Check if user already exists
        if CustomUser.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        if CustomUser.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        
        if errors:
            context = {
                'page_title': 'Register',
                'errors': errors,
                'form_data': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'username': username,
                    'phone_number': phone_number,
                    'role': role,
                },
                'role_choices': ROLE_CHOICES,
            }
            return render(request, 'authentication/register.html', context)
        
        # Create user
        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=role,
            )
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
        except IntegrityError as e:
            messages.error(request, 'An error occurred during registration. Please try again.')
            context = {
                'page_title': 'Register',
                'form_data': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'username': username,
                    'phone_number': phone_number,
                    'role': role,
                },
                'role_choices': ROLE_CHOICES,
            }
            return render(request, 'authentication/register.html', context)
    
    context = {
        'page_title': 'Register',
        'role_choices': ROLE_CHOICES,
    }
    return render(request, 'authentication/register.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')
