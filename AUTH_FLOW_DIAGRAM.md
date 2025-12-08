# 🔐 Authentication System - Flow Diagrams

## Complete User Authentication Flow

```
╔═══════════════════════════════════════════════════════════════════╗
║                    LUMBER MANAGEMENT SYSTEM                       ║
║                                                                    ║
║                    AUTHENTICATION SYSTEM FLOW                     ║
╚═══════════════════════════════════════════════════════════════════╝


┌─────────────────────────────────────────────────────────────────┐
│  1. INITIAL VISIT                                               │
└─────────────────────────────────────────────────────────────────┘

        User visits http://localhost:8000/
                        │
                        ▼
            ┌───────────────────────┐
            │ Is user authenticated?│
            └───────────────────────┘
                  │          │
                YES         NO
                  │          │
                  ▼          ▼
            (Show Home)  (Redirect to Login)
                         /auth/login/


┌─────────────────────────────────────────────────────────────────┐
│  2. LOGIN FLOW                                                   │
└─────────────────────────────────────────────────────────────────┘

        User arrives at /auth/login/
                        │
                        ▼
        ┌────────────────────────────┐
        │ Display Login Form         │
        │ - Username field           │
        │ - Password field           │
        │ - "Sign In" button         │
        │ - "Create Account" link    │
        └────────────────────────────┘
                        │
                        ▼
            User submits credentials
                        │
                        ▼
        ┌────────────────────────────┐
        │ Validate Credentials       │
        │ - Username required        │
        │ - Password required        │
        │ - Authenticate against DB  │
        └────────────────────────────┘
                        │
            ┌───────────┴───────────┐
           NO                       YES
            │                        │
            ▼                        ▼
    ┌──────────────┐     ┌──────────────────┐
    │ Invalid Cred │     │ Create Session   │
    │ Show Error   │     │ Log user in      │
    │ Stay on form │     │ Redirect to home │
    └──────────────┘     └──────────────────┘
                                   │
                                   ▼
                          User sees dashboard


┌─────────────────────────────────────────────────────────────────┐
│  3. REGISTRATION FLOW                                            │
└─────────────────────────────────────────────────────────────────┘

        User clicks "Create Account"
                        │
                        ▼
        Visit /auth/register/
                        │
                        ▼
        ┌────────────────────────────┐
        │ Display Registration Form  │
        │ - First Name               │
        │ - Last Name                │
        │ - Email                    │
        │ - Username                 │
        │ - Phone (optional)         │
        │ - Password                 │
        │ - Confirm Password         │
        │ - Role Dropdown (4 roles)  │
        │ - "Create Account" button  │
        └────────────────────────────┘
                        │
                        ▼
            User submits form
                        │
                        ▼
        ┌────────────────────────────┐
        │ Validate All Fields        │
        └────────────────────────────┘
                        │
            ┌───────────┴───────────┐
        ERRORS                  NO ERRORS
            │                       │
            ▼                       ▼
        ┌──────────────┐    ┌──────────────────┐
        │ Show errors  │    │ Create User      │
        │ - List all   │    │ - Hash password  │
        │   issues     │    │ - Save to DB     │
        │ - Keep form  │    │ - Set role       │
        │   data       │    └──────────────────┘
        └──────────────┘             │
            │                        ▼
            ▼              ┌──────────────────┐
        Retry              │ Account Created  │
                          │ Redirect to      │
                          │ /auth/login/     │
                          └──────────────────┘
                                   │
                                   ▼
                        User can now login


┌─────────────────────────────────────────────────────────────────┐
│  4. AUTHENTICATION VERIFICATION                                  │
└─────────────────────────────────────────────────────────────────┘

        For Protected Routes (like /dashboard/)
                        │
                        ▼
        ┌────────────────────────────┐
        │ @login_required decorator  │
        │ checks if authenticated    │
        └────────────────────────────┘
                        │
            ┌───────────┴───────────┐
        NOT AUTH                  AUTH
            │                       │
            ▼                       ▼
    Redirect to login    Allow access
    (with ?next param)    to route


┌─────────────────────────────────────────────────────────────────┐
│  5. LOGOUT FLOW                                                  │
└─────────────────────────────────────────────────────────────────┘

        User clicks Logout button
                        │
                        ▼
        POST request to /auth/logout/
                        │
                        ▼
        ┌────────────────────────────┐
        │ logout() function          │
        │ - Clear session            │
        │ - Delete session cookie    │
        │ - Remove user from request │
        └────────────────────────────┘
                        │
                        ▼
        ┌────────────────────────────┐
        │ Redirect to /auth/login/   │
        │ Show success message       │
        └────────────────────────────┘
                        │
                        ▼
        User logged out, session cleared
```

---

## Role-Based Access Control

```
┌─────────────────────────────────────────────────────────────────┐
│ USER ROLES & PERMISSIONS                                        │
└─────────────────────────────────────────────────────────────────┘


┌─────────────┐
│    ADMIN    │
└─────────────┘
    │
    ├─→ All Inventory Management
    ├─→ All Sales Operations
    ├─→ All Delivery Management
    ├─→ All Supplier Management
    ├─→ User Management
    ├─→ System Configuration
    ├─→ All Reports
    └─→ Dashboard Analytics


┌──────────────────────┐
│ INVENTORY MANAGER    │
└──────────────────────┘
    │
    ├─→ Stock In/Out
    ├─→ Inventory Adjustments
    ├─→ Low Stock Alerts
    ├─→ Supplier Management
    ├─→ Purchase Orders
    ├─→ Inventory Reports
    └─→ Price Monitoring


┌──────────────┐
│   CASHIER    │
└──────────────┘
    │
    ├─→ Point of Sale (POS)
    ├─→ Sales Orders
    ├─→ Receipt Generation
    ├─→ Customer Management
    ├─→ Payment Tracking
    ├─→ Sales Reports
    └─→ Discounts & Eligibility


┌────────────────────┐
│ WAREHOUSE STAFF    │
└────────────────────┘
    │
    ├─→ Delivery Queue
    ├─→ Picking Lists
    ├─→ Dispatch Management
    ├─→ Delivery Status Updates
    ├─→ Vehicle Assignments
    ├─→ Driver Management
    └─→ Warehouse Reports
```

---

## Session & Authentication State

```
┌─────────────────────────────────────────────────────────────────┐
│ SESSION LIFECYCLE                                                │
└─────────────────────────────────────────────────────────────────┘


STATE 1: NOT AUTHENTICATED
┌─────────────────────────────────┐
│ Session: None                   │
│ User: AnonymousUser             │
│ Cookies: None                   │
│ Access: Public routes only      │
└─────────────────────────────────┘
        │
        │ User registers & logs in
        ▼
STATE 2: AUTHENTICATING
┌─────────────────────────────────┐
│ Session: Creating               │
│ User: Authenticating            │
│ Cookies: Being created          │
│ Access: Checking credentials    │
└─────────────────────────────────┘
        │
        │ Credentials valid
        ▼
STATE 3: AUTHENTICATED
┌─────────────────────────────────┐
│ Session: Active (SESSIONID)     │
│ User: CustomUser(id, role)      │
│ Cookies: sessionid=xxxxx        │
│ Access: Protected routes        │
│ Role: admin/manager/cashier/    │
│        warehouse_staff          │
└─────────────────────────────────┘
        │
        │ User logs out / Session expires
        ▼
STATE 4: LOGGED OUT
┌─────────────────────────────────┐
│ Session: Destroyed              │
│ User: AnonymousUser             │
│ Cookies: sessionid cleared      │
│ Access: Public routes only      │
└─────────────────────────────────┘
```

---

## Request Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ HTTP REQUEST FLOW THROUGH AUTHENTICATION                        │
└─────────────────────────────────────────────────────────────────┘


1. USER SENDS REQUEST
    ├─ Method: GET/POST
    ├─ URL: /auth/login/ (or any path)
    ├─ Headers: Cookie: sessionid=xxxxx (if exists)
    └─ Body: form data (if POST)


2. MIDDLEWARE PROCESSES
    ├─ SessionMiddleware
    │  ├─ Reads sessionid cookie
    │  ├─ Loads session from database
    │  └─ Attaches to request
    │
    ├─ AuthenticationMiddleware
    │  ├─ Gets user from session
    │  ├─ Attaches to request.user
    │  └─ Sets request.user (authenticated or Anonymous)
    │
    └─ CSRFMiddleware
       ├─ Verifies CSRF token
       └─ Prevents cross-site forgery


3. URL ROUTING
    ├─ Match URL pattern
    ├─ Route to correct view
    └─ Check decorators (@login_required, etc.)


4. VIEW EXECUTION
    ├─ Check @login_required decorator
    │  ├─ Is request.user authenticated?
    │  ├─ YES: Continue to view
    │  └─ NO: Redirect to login
    │
    ├─ Check role-based permissions
    │  ├─ if user.role == 'admin'
    │  ├─ Show admin content
    │  └─ else: Show user-appropriate content
    │
    ├─ Process request
    │  ├─ Fetch data
    │  ├─ Validate input
    │  ├─ Update database
    │  └─ Prepare response
    │
    └─ Return response


5. RESPONSE SENT
    ├─ Status: 200, 302 (redirect), etc.
    ├─ Headers: Set-Cookie: sessionid=xxxxx
    ├─ Body: HTML page / JSON / redirect
    └─ Client receives & renders
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ AUTHENTICATION DATA FLOW                                        │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────┐
│   User Form     │
│ - username      │
│ - password      │
└─────────────────┘
        │
        │ POST request
        ▼
┌─────────────────────────────────┐
│ Django Form Handler             │
│ - Validate input                │
│ - Check required fields         │
│ - Sanitize data                 │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│ authenticate() function         │
│ - Query CustomUser by username  │
│ - Check password (hash compare) │
│ - Return user or None           │
└─────────────────────────────────┘
        │
    ┌───┴───┐
   VALID   INVALID
    │       │
    ▼       ▼
  LOGIN  ERROR
    │       │
    ▼       ▼
 ┌─────┐ ┌─────┐
 │YES  │ │NO   │
 └─────┘ └─────┘
    │       │
    ▼       ▼
CREATE    SHOW
SESSION   ERRORS
    │       │
    ▼       ▼
SET       RENDER
COOKIE    FORM
    │       │
    ▼       ▼
REDIR   STAY
TO HOME ON PAGE
```

---

## API Authentication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ REST API AUTHENTICATION                                         │
└─────────────────────────────────────────────────────────────────┘


METHOD 1: SESSION-BASED (Used in Web)

    ┌─────────────┐
    │ Login Form  │
    │  Submit     │
    └─────────────┘
            │
            ▼
    ┌─────────────────────────────────┐
    │ POST /api-auth/login/           │
    │ - username                      │
    │ - password                      │
    └─────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────┐
    │ Django creates session          │
    │ Returns Set-Cookie: sessionid   │
    └─────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────┐
    │ Subsequent Requests             │
    │ Include Cookie: sessionid       │
    │ in each request                 │
    └─────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────┐
    │ Middleware validates session    │
    │ Attaches user to request        │
    │ Allows API access               │
    └─────────────────────────────────┘


METHOD 2: TOKEN-BASED (For External Apps)

    ┌─────────────┐
    │ Get Token   │
    │ (future)    │
    └─────────────┘
            │
            ▼
    ┌─────────────────────────────────┐
    │ Use Token in requests           │
    │ Header: Authorization: Token... │
    └─────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────┐
    │ Validate token                  │
    │ Attach user to request          │
    │ Allow API access                │
    └─────────────────────────────────┘
```

---

## Security Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ SECURITY CHECKS AT EACH STEP                                    │
└─────────────────────────────────────────────────────────────────┘


1. REGISTRATION FORM SUBMISSION
    ├─ ✓ CSRF Token verified
    ├─ ✓ Input sanitized
    ├─ ✓ Email validated
    ├─ ✓ Username length checked
    ├─ ✓ Password strength checked (8+ chars)
    ├─ ✓ Email uniqueness verified (no duplicate)
    ├─ ✓ Username uniqueness verified (no duplicate)
    └─ ✓ Role validated against choices


2. PASSWORD HANDLING
    ├─ ✓ Never stored as plain text
    ├─ ✓ Hashed with bcrypt (Django default)
    ├─ ✓ Salt included in hash
    ├─ ✓ Hash verified on login (constant-time comparison)
    └─ ✓ Never logged or displayed


3. LOGIN FORM SUBMISSION
    ├─ ✓ CSRF Token verified
    ├─ ✓ Username required
    ├─ ✓ Password required
    ├─ ✓ Case-sensitive password comparison
    ├─ ✓ No user enumeration (same error for all failures)
    └─ ✓ Rate limiting (optional future enhancement)


4. SESSION CREATION
    ├─ ✓ Session ID generated (cryptographically random)
    ├─ ✓ Stored in database
    ├─ ✓ Cookie set with secure flags (configurable)
    ├─ ✓ HttpOnly flag (no JavaScript access)
    ├─ ✓ SameSite protection (against CSRF)
    └─ ✓ Expiration set (configurable)


5. PROTECTED ROUTE ACCESS
    ├─ ✓ Session ID verified
    ├─ ✓ User loaded from session
    ├─ ✓ User.is_authenticated checked
    ├─ ✓ Role verified if needed
    └─ ✓ Redirect to login if not authenticated


6. LOGOUT
    ├─ ✓ POST method required (CSRF protection)
    ├─ ✓ Session destroyed
    ├─ ✓ Cookie cleared
    ├─ ✓ User reference removed
    └─ ✓ Cannot reuse old session ID
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ ERROR SCENARIOS & HANDLING                                      │
└─────────────────────────────────────────────────────────────────┘


REGISTRATION ERRORS
├─ Empty field → "Field is required"
├─ Password < 8 chars → "Password must be 8+ chars"
├─ Passwords don't match → "Passwords do not match"
├─ Email exists → "Email already registered"
├─ Username exists → "Username already exists"
├─ Invalid email → "Invalid email format"
├─ Invalid phone → "Invalid phone number"
└─ Invalid role → "Invalid role selected"


LOGIN ERRORS
├─ Empty username → "Username required"
├─ Empty password → "Password required"
├─ Wrong credentials → "Invalid username or password"
└─ User inactive → "Account is inactive"


PROTECTED ROUTE ERRORS
├─ Not logged in → Redirect to /auth/login/?next=path
├─ Session expired → Redirect to /auth/login/
├─ Wrong role → "Access Denied" (implement in future)
└─ Invalid token → "Invalid request"


ERROR DISPLAY
├─ Form stays on page
├─ All inputs retain values (except password)
├─ Error list shows clearly
├─ Messages disappear after navigation
└─ No sensitive info exposed
```

---

**These diagrams show the complete authentication flow from user perspective to system perspective.**

