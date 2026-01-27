# Fix: Duplicate Notifications for Order Confirmation

## Problem Identified
Customers were receiving **2 duplicate "Order Ready for Pickup" notifications** plus an initial "Order Confirmed" notification when orders were created and then confirmed:

1. **Initial notification** - "Order Confirmed" (when order is created)
2. **First ready notification** - "Order Ready for Pickup" (when admin confirms)
3. **Duplicate ready notification** - "Order Ready for Pickup" (milliseconds later)

### Example from Database
```
Order SO-20260127-0010:
  ready_for_pickup notification 1: ID 243, Created 14:28:49.903
  ready_for_pickup notification 2: ID 244, Created 14:28:49.925  ← Duplicate!
  order_confirmed notification: ID 242, Created 14:28:37.419
```

## Root Causes

### Issue 1: Double Confirmation in API
In `app_sales/views.py` confirm_order():
1. Line 74: Called `order.save()` which triggers signal
2. Line 79: Manually called `confirmation.mark_ready_for_pickup()` again
3. Result: `mark_ready_for_pickup()` created notification twice

### Issue 2: Unnecessary Initial Notification
In `app_sales/services.py` create_order_confirmation():
- Creating an "Order Confirmed" notification when order is created
- Then another "Order Ready for Pickup" when admin confirms
- User gets notified twice about the same order

## Solution

### Fix 1: Remove Duplicate Call in Views
**File**: `app_sales/views.py`

Changed from:
```python
order.save()

# Mark order as ready for pickup and notify customer
try:
    confirmation = order.confirmation
    confirmation.mark_ready_for_pickup()
except Exception as e:
    print(f"Warning: Could not mark order...")
```

To:
```python
# The signal will automatically call confirmation.mark_ready_for_pickup()
# which creates the notification and updates the confirmation status
order.is_confirmed = True
order.confirmed_at = timezone.now()
order.confirmed_by = request.user
order.save()
```

**Why**: The post_save signal already calls `mark_ready_for_pickup()`, so no need to call it manually.

### Fix 2: Skip Initial "Order Confirmed" Notification
**File**: `app_sales/services.py`

Changed `create_order_confirmation()` to accept `send_notification` parameter:

```python
def create_order_confirmation(
    sales_order_id, 
    estimated_pickup_date=None, 
    created_by=None, 
    send_notification=True  # NEW parameter
):
    # ... create confirmation ...
    
    if send_notification:
        # Create initial notification
        OrderNotification.objects.create(...)
```

And in `create_sales_order()`:
```python
OrderConfirmationService.create_order_confirmation(
    sales_order_id=so.id,
    estimated_pickup_date=estimated_pickup_date,
    created_by=created_by,
    send_notification=False  # Don't notify on creation
)
```

**Why**: Customers should only be notified once - when the order is READY, not when it's created.

## Notification Flow - After Fix

### Creating an Order
1. SalesOrder created
2. OrderConfirmation created
3. **No notification sent** (send_notification=False)
4. Customer sees nothing yet

### Admin Confirms Order
1. Admin sets is_confirmed = True in Django admin
2. save_model() sets confirmed_at and confirmed_by
3. post_save signal fires
4. Signal calls confirmation.mark_ready_for_pickup()
5. **Single "Order Ready for Pickup" notification created**
6. Customer sees notification badge
7. Customer can click to view order

## Benefits

✅ **Single notification** - Only "Order Ready for Pickup" notification
✅ **No duplicates** - Fixed double call issue in API
✅ **Better UX** - Customer knows exactly when to pick up, not just that order was created
✅ **Backward compatible** - send_notification parameter defaults to True
✅ **Flexible** - Can create confirmations without notifications if needed

## Testing

Before fix:
```
Notifications for SO-20260127-0008:
  1. order_confirmed (ID 236) - "Order Confirmed"
  2. ready_for_pickup (ID 237) - "Order Ready for Pickup"
  3. ready_for_pickup (ID 238) - "Order Ready for Pickup" ← DUPLICATE
```

After fix:
```
Notifications for new orders:
  1. ready_for_pickup (ID 1) - "Order Ready for Pickup" ← Single notification
```

## Files Changed
1. `app_sales/views.py` - Removed duplicate confirmation call
2. `app_sales/services.py` - Added send_notification parameter

## Status
✅ Fixed - No more duplicate notifications
✅ No more initial "Order Confirmed" notification
✅ Single "Order Ready for Pickup" when admin confirms
✅ Backward compatible with existing code
