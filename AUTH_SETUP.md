# Authentication System Setup - Complete

## Overview
Login and registration system fully integrated with the Lumber Management System.

## Files Created/Modified

### New Files
1. **app_authentication/urls.py** - URL routing for auth views
2. **app_authentication/views.py** - Login, register, and logout views
3. **templates/authentication/login.html** - Login page with Tailwind styling
4. **templates/authentication/register.html** - Registration page with role selection

### Modified Files
1. **core/views.py** - Added `home` view with auth redirect
2. **lumber/urls.py** - Added auth URL routing and core URL inclusion

## Features

### Login View (`/auth/login/`)
- Username/password authentication
- Redirect authenticated users to home
- Error messaging for invalid credentials
- Remember username field on error
- Link to register page
- Tailwind CSS styled responsive design

### Register View (`/auth/register/`)
- First name, last name, email, username
- Phone number (optional, with validation)
- Password confirmation
- Role selection (Admin, Inventory Manager, Cashier, Warehouse Staff)
- Comprehensive validation:
  - Duplicate username/email checking
  - Password strength (min 8 chars)
  - Password match validation
  - All required fields validation
- Error display with specific messages
- Link to login page

### Logout View (`/auth/logout/`)
- POST-only endpoint (secure)
- Requires authentication
- Clears session and redirects to login

## User Roles Available
1. **Admin** - Full system control
2. **Inventory Manager** - Stock and purchasing management
3. **Cashier** - Sales and POS operations
4. **Warehouse Staff** - Delivery and warehouse operations

## Flow
```
Landing Page (/) 
    ↓
[Not Authenticated?] 
    ↓ (Yes)
Login Page (/auth/login/)
    ↓
[Registered?]
    ├─ (No) → Register Page (/auth/register/) → Create Account → Login
    └─ (Yes) → Authenticate → Home/Landing
    ↓
Authenticated User
```

## Settings
- AUTH_USER_MODEL = 'core.CustomUser'
- App installed in INSTALLED_APPS
- CSRF protection enabled
- Session-based authentication

## Usage

### For Users
1. Navigate to `/auth/login/` to sign in
2. New users: Click "Create an Account" link on login page
3. Fill registration form with role selection
4. Account created automatically
5. Log in with new credentials
6. Access dashboard and authenticated pages

### For Admins
- Create users via Django admin: `/admin/core/customuser/`
- Assign roles and permissions
- Manage user status (active/inactive)

## Testing
1. Run migrations: `python manage.py migrate`
2. Create superuser: `python manage.py createsuperuser`
3. Visit `/auth/register/` to create a test user
4. Visit `/auth/login/` to test login
5. Check `/` (home) - should redirect to login if not authenticated

## API Integration
- REST API endpoints protected with `IsAuthenticated` permission
- Token-based authentication available via `/api-auth/`
- User info available at `/api/users/me/`
- Users can be filtered by role via `/api/users/by_role/?role=admin`

## Security Features
- CSRF protection on all forms
- Session-based auth
- Password hashing (Django default)
- Email validation
- Phone number regex validation
- Duplicate account prevention
- Secure logout (clears session)
