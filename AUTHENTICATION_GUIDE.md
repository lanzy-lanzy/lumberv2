# Authentication System - Quick Start Guide

## What's Been Set Up

A complete login and registration system integrated with your Lumber Management System.

### New Routes
- **`/auth/login/`** — User login page
- **`/auth/register/`** — User registration page
- **`/auth/logout/`** — User logout (POST)
- **`/`** (Home) — Landing page (requires authentication)

## Quick Start

### 1. Start the Server
```bash
python manage.py runserver
```

### 2. First-Time Setup
Visit: `http://localhost:8000/auth/register/`

Fill in:
- First Name
- Last Name
- Email
- Username
- Password (min 8 characters)
- Role (choose one):
  - Admin
  - Inventory Manager
  - Cashier
  - Warehouse Staff

### 3. Login
Visit: `http://localhost:8000/auth/login/`

Enter your username and password.

### 4. Access Dashboard
Once logged in, you'll be redirected to the landing page (`/`).

## Files Created

```
templates/
├── authentication/
│   ├── login.html       ← User login form
│   └── register.html    ← User registration form

app_authentication/
├── views.py             ← Authentication logic
├── urls.py              ← Auth routes
└── [existing files]
```

## User Roles & Permissions

| Role | Purpose |
|------|---------|
| **Admin** | Full system access, user management, all reports |
| **Inventory Manager** | Stock control, purchasing, inventory reports |
| **Cashier** | Sales orders, POS, receipts |
| **Warehouse Staff** | Delivery management, picking, dispatch |

## Authentication Flow

```
User visits /
  ↓
Not authenticated?
  ├─ Yes → Redirect to /auth/login/
  └─ No → Show landing page
  
User visits /auth/login/
  ├─ Existing user → Enter credentials → Login
  └─ New user → Click "Create Account" → /auth/register/

At /auth/register/
  ├─ Fill form → Select role → Submit
  └─ Account created → Redirect to /auth/login/

Successful login
  → Redirect to / (home/landing)
  → User sees dashboard based on role
```

## Default Admin User (Optional)

Create an admin account via Django admin:

```bash
python manage.py createsuperuser
```

Then visit: `http://localhost:8000/admin/`

## API Authentication

The API (`/api/`) uses session-based authentication.

### Authenticate via API
```bash
curl -X POST http://localhost:8000/api-auth/login/ \
  -d "username=yourusername&password=yourpassword"
```

### Get Current User Info
```bash
curl http://localhost:8000/api/users/me/ \
  -H "Cookie: sessionid=your_session_id"
```

## Customization

### Styling
Both templates use **Tailwind CSS CDN**. Modify the color scheme:

In `login.html` and `register.html`:
- Change `bg-amber-600` to your preferred color (e.g., `bg-blue-600`)
- All utilities are Tailwind classes

### Password Requirements
Edit `app_authentication/views.py`:

```python
if len(password) < 8:  # Change minimum length here
    errors.append('Password must be at least 8 characters long.')
```

### Email Validation
Optional phone number validation is enabled. To make it required:

In `app_authentication/views.py`:
```python
if not phone_number:
    errors.append('Phone number is required.')
```

## Troubleshooting

### Users table doesn't exist
```bash
python manage.py migrate
```

### Forgot password?
Create a new user account via registration.

For existing users, reset via Django admin (`/admin/`):
1. Go to Core → Custom Users
2. Select user
3. Click on password field
4. Set new password

### Registration failing with "User already exists"
Check `/admin/core/customuser/` to see existing users.

## Security Notes

✅ **Enabled:**
- CSRF protection on forms
- Password hashing (Django default)
- Session-based auth
- Email uniqueness validation
- Username uniqueness validation

✅ **Recommended for production:**
- Enable HTTPS (set `SECURE_SSL_REDIRECT = True`)
- Set `SESSION_COOKIE_SECURE = True`
- Set `CSRF_COOKIE_SECURE = True`
- Use strong `SECRET_KEY`

## Testing Users

Create test accounts for each role:

1. **Admin User**
   - Username: `admin1`
   - Role: Admin
   - Password: `SecurePassword123`

2. **Inventory Manager**
   - Username: `inventory1`
   - Role: Inventory Manager
   - Password: `SecurePassword123`

3. **Cashier**
   - Username: `cashier1`
   - Role: Cashier
   - Password: `SecurePassword123`

4. **Warehouse Staff**
   - Username: `warehouse1`
   - Role: Warehouse Staff
   - Password: `SecurePassword123`

Register each via `/auth/register/`.

## Next Steps

1. ✅ Authentication system is live
2. ⬜ Update landing page to show role-specific content
3. ⬜ Protect dashboard routes with role checks
4. ⬜ Add "Forgot Password" functionality (optional)
5. ⬜ Add 2FA/MFA (optional)

---

**Questions?** Check the `AUTH_SETUP.md` file for technical details.
