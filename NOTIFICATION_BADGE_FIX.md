# Notification Badge Display Fix

## Problem
When orders were confirmed and customers received notifications, the notification badge did not appear in the sidebar showing the unread notification count. The notifications were being created correctly but the badge was not displaying.

## Root Cause
The context processor was looking up the customer by `email=request.user.email`, but:
1. Some customers in the system had `NULL` email fields
2. The CustomUser (Django user) also might not have the same email as the Customer record
3. The customer lookup would fail silently, causing the context processor to return an empty context without notification counts

## Solution
Updated the customer lookup logic in two places:

### 1. Context Processor (`app_sales/context_processors.py`)
Added fallback logic to find customer by name if email lookup fails:

```python
# Try to find customer by email first, then by name
sales_customer = SalesCustomer.objects.filter(
    email=request.user.email
).first()

if not sales_customer and request.user.email:
    # If email lookup failed but user has an email, return empty context
    return context

if not sales_customer:
    # Fallback: try to find customer by first/last name if email is not unique
    full_name = request.user.get_full_name()
    if full_name:
        sales_customer = SalesCustomer.objects.filter(
            name=full_name
        ).first()

if not sales_customer:
    return context
```

### 2. Notification Views (`app_sales/notification_views.py`)
Updated three views to use the same fallback logic:
- `customer_notifications()` - Displays notification page and sidebar badge
- `customer_ready_orders()` - Shows orders ready for pickup
- `customer_dashboard()` - Shows dashboard with notification summary

```python
# Try to find customer by email first, then by name
customer = SalesCustomer.objects.filter(
    email=request.user.email
).first()

if not customer:
    full_name = request.user.get_full_name()
    if full_name:
        customer = SalesCustomer.objects.filter(name=full_name).first()

if not customer:
    # Handle no customer case
    ...
```

## Result
- Notification badge now displays correctly in the sidebar
- Shows count of unread notifications (e.g., "3")
- Badge appears for customers regardless of whether they have an email set
- Falls back to name-based lookup when email is unavailable

## Testing
When a customer with no email field:
1. Admin confirms order in Django admin
2. Customer receives notification
3. Context processor now finds customer by name
4. `notification_count` is passed to sidebar template
5. Badge displays the count of unread notifications

## Impact
- No breaking changes
- Improves robustness of customer lookups
- Works for existing customers with missing emails
- Better user experience with visible notification indicators
