"""
Views for customer order notifications and status tracking
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from app_sales.models import Customer as SalesCustomer
from app_sales.notification_models import OrderNotification, OrderConfirmation
from app_sales.services import OrderConfirmationService


@login_required
def customer_notifications(request):
    """Display all notifications for authenticated customer"""
    try:
        # Use unified lookup logic from SalesService
        from app_sales.services import SalesService
        customer = SalesService.get_customer_for_user(request.user)
        
        if not customer:
            notifications = []
            unread_count = 0
        else:
            notifications = OrderNotification.objects.filter(
                customer=customer
            ).select_related('sales_order').order_by('-created_at')
            
            unread_count = notifications.filter(is_read=False).count()
        
        context = {
            'notifications': notifications,
            'unread_count': unread_count,
            'total_count': notifications.count() if customer else 0,
        }
        return render(request, 'customer/notifications.html', context)
    except Exception as e:
        return render(request, 'customer/notifications.html', {'error': str(e)})


@login_required
def customer_ready_orders(request):
    """Display orders ready for pickup"""
    try:
        # Use unified lookup logic from SalesService
        from app_sales.services import SalesService
        customer = SalesService.get_customer_for_user(request.user)
        
        if not customer:
            ready_orders = []
            pending_payment = []
        else:
            ready_orders = OrderConfirmation.objects.filter(
                customer=customer,
                status='ready_for_pickup'
            ).select_related('sales_order').order_by('-ready_at')
            
            pending_payment = OrderConfirmation.objects.filter(
                customer=customer,
                status__in=['confirmed', 'ready_for_pickup'],
                is_payment_complete=False
            ).select_related('sales_order').order_by('-created_at')
        
        context = {
            'ready_orders': ready_orders,
            'ready_count': ready_orders.count() if customer else 0,
            'pending_payment': pending_payment,
            'pending_count': pending_payment.count() if customer else 0,
        }
        return render(request, 'customer/ready_orders.html', context)
    except Exception as e:
        return render(request, 'customer/ready_orders.html', {'error': str(e)})


@login_required
def customer_dashboard(request):
    """Customer dashboard with order summary"""
    try:
        # Use unified lookup logic from SalesService
        from app_sales.services import SalesService
        customer = SalesService.get_customer_for_user(request.user)
        
        if not customer:
            context = {
                'customer': None,
                'ready_orders': [],
                'recent_notifications': [],
                'pending_payment': [],
            }
        else:
            from django.db.models import Sum
            from app_sales.models import SalesOrder
            
            # Get all customer orders
            customer_orders = SalesOrder.objects.filter(customer=customer)
            
            # Calculate totals
            order_count = customer_orders.count()
            total_spent = customer_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            # Get recent orders for display
            recent_orders = customer_orders.order_by('-created_at')[:10]
            
            ready_orders = OrderConfirmation.objects.filter(
                customer=customer,
                status='ready_for_pickup'
            ).select_related('sales_order').order_by('-ready_at')[:5]
            
            recent_notifications = OrderNotification.objects.filter(
                customer=customer
            ).select_related('sales_order').order_by('-created_at')[:10]
            
            pending_payment = OrderConfirmation.objects.filter(
                customer=customer,
                status__in=['confirmed', 'ready_for_pickup'],
                is_payment_complete=False
            ).select_related('sales_order').order_by('-created_at')[:5]
            
            unread_count = OrderNotification.objects.filter(
                customer=customer,
                is_read=False
            ).count()
            
            context = {
                'customer': customer,
                'order_count': order_count,
                'total_spent': total_spent,
                'sales_orders': recent_orders,
                'ready_orders': ready_orders,
                'ready_count': ready_orders.count(),
                'recent_notifications': recent_notifications,
                'notification_count': unread_count,
                'pending_payment': pending_payment,
                'pending_count': pending_payment.count(),
            }
        
        return render(request, 'customer/dashboard.html', context)
    except Exception as e:
        return render(request, 'customer/dashboard.html', {'error': str(e)})


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = OrderNotification.objects.get(id=notification_id)
        
        # Verify customer owns this notification
        # Use unified lookup logic from SalesService
        from app_sales.services import SalesService
        customer = SalesService.get_customer_for_user(request.user)
        
        if not customer or notification.customer != customer:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        notification.mark_as_read()
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
    except OrderNotification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read for customer"""
    try:
        # Use unified lookup logic from SalesService
        from app_sales.services import SalesService
        customer = SalesService.get_customer_for_user(request.user)
        
        if not customer:
            return JsonResponse({'count': 0})
        
        unread = OrderNotification.objects.filter(
            customer=customer,
            is_read=False
        )
        count = unread.count()
        
        for notif in unread:
            notif.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'count': count,
            'message': f'Marked {count} notifications as read'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def order_confirmation_detail(request, confirmation_id):
    """View order confirmation details"""
    try:
        confirmation = OrderConfirmation.objects.select_related(
            'sales_order', 'customer'
        ).get(id=confirmation_id)
        
        # Verify customer owns this order
        # Use unified lookup logic from SalesService
        from app_sales.services import SalesService
        customer = SalesService.get_customer_for_user(request.user)
        if not customer or confirmation.customer != customer:
            return redirect('customer-dashboard')
        
        # Get related notifications
        notifications = OrderNotification.objects.filter(
            sales_order=confirmation.sales_order
        ).order_by('-created_at')
        
        context = {
            'confirmation': confirmation,
            'sales_order': confirmation.sales_order,
            'notifications': notifications,
        }
        return render(request, 'customer/order_confirmation_detail.html', context)
    except OrderConfirmation.DoesNotExist:
        return redirect('customer-dashboard')
    except Exception as e:
        return render(request, 'customer/order_confirmation_detail.html', {'error': str(e)})


@login_required
@require_POST
def confirm_order_pickup(request, confirmation_id):
    """Confirm customer pickup of order"""
    try:
        confirmation = OrderConfirmation.objects.get(id=confirmation_id)
        
        # Verify customer owns this order
        # Use unified lookup logic from SalesService
        from app_sales.services import SalesService
        customer = SalesService.get_customer_for_user(request.user)
        if not customer or confirmation.customer != customer:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        if confirmation.status != 'ready_for_pickup':
            return JsonResponse({
                'error': 'Order is not ready for pickup'
            }, status=400)
        
        # Mark as picked up
        OrderConfirmationService.mark_order_picked_up(
            sales_order_id=confirmation.sales_order_id
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you! Your order has been picked up.',
            'status': 'picked_up'
        })
    except OrderConfirmation.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def notification_badge_count(request):
    """Get notification count for AJAX updates"""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    
    try:
        # Use unified lookup logic from SalesService
        from app_sales.services import SalesService
        customer = SalesService.get_customer_for_user(request.user)
        
        if not customer:
            return JsonResponse({'count': 0})
        
        count = OrderNotification.objects.filter(
            customer=customer,
            is_read=False
        ).count()
        
        return JsonResponse({
            'count': count,
            'customer_id': customer.id
        })
    except Exception as e:
        return JsonResponse({'count': 0, 'error': str(e)})
