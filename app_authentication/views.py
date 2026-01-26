from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db import IntegrityError
from core.models import CustomUser, ROLE_CHOICES, USER_TYPE_CHOICES, CustomerProfile


@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
            return render(request, 'authentication/login.html')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Refresh user from DB before login to ensure clean state
            user.refresh_from_db()
            
            # Check if customer is approved
            if user.is_customer() and not user.is_approved:
                messages.error(request, 'Your account is pending admin approval. Please check your email for approval status.')
                return render(request, 'authentication/login.html', {'username': username})
            
            import sys
            print(f"DEBUG: Login successful for {user.username}, is_customer={user.is_customer()}", file=sys.stderr)
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Get next URL from request, or redirect based on user type
            next_url = request.GET.get('next')
            if next_url:
                print(f"DEBUG: Redirecting to next_url: {next_url}", file=sys.stderr)
                return redirect(next_url)
            
            # Redirect based on user type
            if user.is_customer():
                print(f"DEBUG: User is customer, redirecting to customer-dashboard", file=sys.stderr)
                return redirect('customer-dashboard')
            else:
                print(f"DEBUG: User is employee, redirecting to dashboard", file=sys.stderr)
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
    """User registration view for both employees and customers"""
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
        user_type = request.POST.get('user_type', 'employee').strip()
        role = request.POST.get('role', '').strip() if user_type == 'employee' else None
        address = request.POST.get('address', '').strip() if user_type == 'customer' else ''
        is_senior = request.POST.get('is_senior') == 'true' if user_type == 'customer' else False
        is_pwd = request.POST.get('is_pwd') == 'true' if user_type == 'customer' else False
        id_document = request.FILES.get('id_document') if user_type == 'customer' else None
        
        # Validation
        errors = []
        
        if not first_name:
            errors.append('First name is required.')
        if not last_name:
            errors.append('Last name is required.')
        if not username:
            errors.append('Username is required.')
        if not password:
            errors.append('Password is required.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        if password != password_confirm:
            errors.append('Passwords do not match.')
        
        # User type validation
        if user_type not in [choice[0] for choice in USER_TYPE_CHOICES]:
            errors.append('Invalid user type selected.')
        
        # Role validation for employees
        if user_type == 'employee':
            if not role:
                errors.append('Role is required for employees.')
            elif role not in [choice[0] for choice in ROLE_CHOICES]:
                errors.append('Invalid role selected.')
        
        # ID document validation for customers
        if user_type == 'customer':
            if not id_document:
                errors.append('ID document is required for customer registration.')
            elif id_document.size > 5242880:  # 5MB limit
                errors.append('ID document must be less than 5MB.')
        
        # Check if user already exists
        if CustomUser.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        if email and CustomUser.objects.filter(email=email).exists():
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
                    'user_type': user_type,
                    'role': role,
                    'address': address,
                    'is_senior': 'true' if is_senior else '',
                    'is_pwd': 'true' if is_pwd else '',
                    'id_document': id_document.name if id_document else '',
                },
                'role_choices': ROLE_CHOICES,
            }
            return render(request, 'authentication/register.html', context)
        
        # Create user
        try:
            # For customers, set is_approved to False (requires admin approval)
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                user_type=user_type,
                role=role if user_type == 'employee' else None,
                is_approved=True if user_type == 'employee' else False,
                id_document=id_document if user_type == 'customer' else None,
            )
            
            # Create customer profile if user is a customer
            if user_type == 'customer':
                CustomerProfile.objects.create(
                    user=user,
                    address=address,
                    is_senior=is_senior,
                    is_pwd=is_pwd,
                )
                messages.success(request, 'Account created successfully! Your ID has been submitted for admin approval. You will be able to login once approved.')
                return redirect('login')
            
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
                    'user_type': user_type,
                    'role': role,
                    'address': address,
                    'is_senior': 'true' if is_senior else '',
                    'is_pwd': 'true' if is_pwd else '',
                },
                'role_choices': ROLE_CHOICES,
            }
            return render(request, 'authentication/register.html', context)
    
    context = {
        'page_title': 'Register',
        'form_data': {'user_type': 'employee'},
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


@login_required
@require_http_methods(["GET"])
def pending_registrations_view(request):
    """View pending customer registrations for admin approval"""
    # Only admins can access this view
    if not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    # Get all unapproved customer registrations
    pending_users = CustomUser.objects.filter(
        user_type='customer',
        is_approved=False
    ).select_related('customer_profile').order_by('-created_at')
    
    context = {
        'page_title': 'Pending Registrations',
        'pending_users': pending_users,
        'pending_count': pending_users.count(),
    }
    return render(request, 'authentication/pending_registrations.html', context)


@login_required
@require_http_methods(["POST"])
def approve_registration_view(request, user_id):
    """Approve a pending customer registration"""
    # Only admins can access this view
    if not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    try:
        user = CustomUser.objects.get(id=user_id, user_type='customer', is_approved=False)
        user.is_approved = True
        user.save()
        messages.success(request, f'{user.get_full_name()} has been approved and can now login.')
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found or already approved.')
    
    return redirect('pending_registrations')


@login_required
@require_http_methods(["POST"])
def reject_registration_view(request, user_id):
    """Reject a pending customer registration"""
    # Only admins can access this view
    if not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    try:
        user = CustomUser.objects.get(id=user_id, user_type='customer', is_approved=False)
        email = user.email
        user.delete()
        messages.success(request, f'Registration for {email} has been rejected and deleted.')
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found or already approved.')
    
    return redirect('pending_registrations')


@login_required
@require_http_methods(["GET"])
def user_list_view(request):
    """View all users list (admin only)"""
    if not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    users = CustomUser.objects.all().order_by('-created_at')
    
    # Filter by user type if provided
    user_type = request.GET.get('user_type')
    if user_type:
        users = users.filter(user_type=user_type)
        
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        from django.db.models import Q
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    context = {
        'page_title': 'User Management',
        'users': users,
        'user_type': user_type,
        'search_query': search_query,
    }
    return render(request, 'authentication/user_list.html', context)


@login_required
@require_http_methods(["GET"])
def customer_user_list_view(request):
    """View only customer users list (admin only)"""
    if not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    customers = CustomUser.objects.filter(user_type='customer').select_related('customer_profile').order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        from django.db.models import Q
        customers = customers.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    context = {
        'page_title': 'Customer Management',
        'customers': customers,
        'search_query': search_query,
    }
    return render(request, 'authentication/customer_user_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def add_user_view(request):
    """Add a new user by admin"""
    if not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        user_type = request.POST.get('user_type', 'employee').strip()
        role = request.POST.get('role', '').strip() if user_type == 'employee' else None
        
        # Validation
        errors = []
        if not first_name or not last_name or not username or not password:
            errors.append('All required fields must be filled.')
        
        if CustomUser.objects.filter(username=username).exists():
            errors.append('Username already exists.')
            
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number,
                    user_type=user_type,
                    role=role,
                    is_approved=True # Admin created users are auto-approved
                )
                
                if user_type == 'customer':
                    address = request.POST.get('address', '').strip()
                    is_senior = request.POST.get('is_senior') == 'on'
                    is_pwd = request.POST.get('is_pwd') == 'on'
                    CustomerProfile.objects.create(
                        user=user,
                        address=address,
                        is_senior=is_senior,
                        is_pwd=is_pwd
                    )
                
                messages.success(request, f'User {username} created successfully.')
                if user_type == 'customer':
                    return redirect('customer_user_list')
                return redirect('user_list')
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')

    context = {
        'page_title': 'Add New User',
        'role_choices': ROLE_CHOICES,
        'user_type_choices': USER_TYPE_CHOICES,
    }
    return render(request, 'authentication/add_user.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_user_status_view(request, user_id):
    """Toggle a user's is_active status (admin only)"""
    if not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    # Prevent admin from deactivating themselves
    if request.user.id == user_id:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('user_list')
    
    try:
        user = CustomUser.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()
        status = "activated" if user.is_active else "deactivated"
        messages.success(request, f'User {user.username} has been {status}.')
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
    
    return redirect(request.META.get('HTTP_REFERER', 'user_list'))


@login_required
@require_http_methods(["POST"])
def delete_user_view(request, user_id):
    """Delete a user account (admin only)"""
    if not request.user.is_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')
    
    # Prevent admin from deleting themselves
    if request.user.id == user_id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    
    try:
        user = CustomUser.objects.get(id=user_id)
        
        # Safety checks for customers with orders (if applicable)
        if user.is_customer():
            from app_sales.models import SalesOrder
            if SalesOrder.objects.filter(customer__name=user.get_full_name()).exists(): # Simplified check based on existing relations
                messages.error(request, f'Cannot delete user {user.username} as they have existing sales records.')
                return redirect('customer_user_list')

        username = user.username
        user.delete()
        messages.success(request, f'User {username} has been permanently deleted.')
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found.')
    except Exception as e:
        messages.error(request, f'Error deleting user: {str(e)}')
    
    return redirect(request.META.get('HTTP_REFERER', 'user_list'))
