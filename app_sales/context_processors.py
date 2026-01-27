"""
Context processor for order notifications.
Adds pending notifications and order confirmations to all templates.
"""

from app_sales.notification_models import OrderNotification, OrderConfirmation
from app_sales.models import Customer as SalesCustomer
from django.db.models import Q
from django.utils import timezone


def order_notifications(request):
    """
    Add order notifications to template context.
    Only processes authenticated users who are customers.
    
    Available in templates as:
    - notifications: Unread notifications with details
    - notification_count: Count of unread notifications
    - pending_orders: Orders ready for pickup
    - pending_orders_count: Count of orders ready for pickup
    - ready_pickups: Orders ready for pickup with payment status
    - ready_pickups_count: Count of orders ready for pickup
    - payment_pending_orders: Orders with payment pending
    - payment_pending_count: Count of orders with payment pending
    - has_ready_pickup_notifications: Boolean if customer has orders ready
    """
    context = {
        'notifications': [],
        'notification_count': 0,
        'notification_alerts': {
            'ready_for_pickup': 0,
            'payment_completed': 0,
            'payment_pending': 0,
            'order_confirmed': 0,
        },
        'pending_orders': [],
        'pending_orders_count': 0,
        'ready_pickups': [],
        'ready_pickups_count': 0,
        'payment_pending_orders': [],
        'payment_pending_count': 0,
        'has_ready_pickup_notifications': False,
        'has_payment_notifications': False,
    }
    
    # Only process authenticated users
    if not request.user.is_authenticated:
        return context

    # Admin/Staff Notifications
    if request.user.is_staff or getattr(request.user, 'role', '') in ['admin', 'sales_staff', 'inventory_manager']:
        try:
            # Count incoming orders (OrderConfirmation with status='created')
            incoming_count = OrderConfirmation.objects.filter(status='created').count()
            context['admin_incoming_count'] = incoming_count
        except Exception:
            pass
    
    # Customer Notifications logic
    try:
        from app_sales.services import SalesService
        sales_customer = SalesService.get_customer_for_user(request.user)
        
        if not sales_customer:
            return context
        
        # Get unread notifications for customer
        notifications = OrderNotification.objects.filter(
            customer=sales_customer,
            is_read=False
        ).select_related('sales_order').order_by('-created_at')
        
        # Build notification list with details
        notification_list = []
        for notif in notifications[:20]:  # Limit to 20 most recent
            notification_list.append({
                'id': notif.id,
                'type': notif.notification_type,
                'title': notif.title,
                'message': notif.message,
                'order_number': notif.sales_order.so_number if notif.sales_order else None,
                'created_at': notif.created_at,
                'is_read': notif.is_read,
            })
            # Count by type
            if notif.notification_type in context['notification_alerts']:
                context['notification_alerts'][notif.notification_type] += 1
        
        context['notifications'] = notification_list
        context['notification_count'] = notifications.count()
        
        # Get orders ready for pickup
        ready_orders = OrderConfirmation.objects.filter(
            customer=sales_customer,
            status='ready_for_pickup'
        ).select_related('sales_order').order_by('-ready_at')
        
        context['pending_orders'] = ready_orders
        context['pending_orders_count'] = ready_orders.count()
        context['has_ready_pickup_notifications'] = ready_orders.exists()
        
        # Get detailed ready pickups with payment info
        ready_pickups = []
        for confirmation in ready_orders[:5]:  # Limit to 5
            so = confirmation.sales_order
            days_ready = (timezone.now() - confirmation.ready_at).days if confirmation.ready_at else 0
            
            pickup_data = {
                'id': confirmation.id,
                'order_number': so.so_number,
                'total_amount': float(so.total_amount),
                'discount_amount': float(so.discount_amount),
                'amount_paid': float(so.amount_paid),
                'balance': float(so.balance),
                'payment_complete': confirmation.is_payment_complete,
                'estimated_pickup': confirmation.estimated_pickup_date,
                'ready_since': confirmation.ready_at,
                'days_ready': days_ready,
                'confirmation': confirmation,
                'payment_status': 'PAID' if confirmation.is_payment_complete else f'DUE: ₱{so.balance:.2f}',
            }
            ready_pickups.append(pickup_data)
        
        context['ready_pickups'] = ready_pickups
        context['ready_pickups_count'] = len(ready_pickups)
        
        # Get orders with payment pending
        payment_pending = OrderConfirmation.objects.filter(
            customer=sales_customer,
            status__in=['confirmed', 'ready_for_pickup'],
            is_payment_complete=False
        ).select_related('sales_order').order_by('-created_at')
        
        payment_pending_list = []
        for confirmation in payment_pending[:5]:  # Limit to 5
            so = confirmation.sales_order
            payment_pending_list.append({
                'id': confirmation.id,
                'order_number': so.so_number,
                'total_amount': float(so.total_amount),
                'balance_due': float(so.balance),
                'status': confirmation.get_status_display(),
                'confirmation': confirmation,
            })
        
        context['payment_pending_orders'] = payment_pending_list
        context['payment_pending_count'] = payment_pending.count()
        context['has_payment_notifications'] = payment_pending.exists()
        
    except Exception as e:
        # Silently fail - don't break template rendering
        pass
    
    return context
