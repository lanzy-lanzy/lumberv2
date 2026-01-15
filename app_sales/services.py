"""
Sales management services for Sales Orders, POS, and Receipts
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from app_sales.models import Customer, SalesOrder, SalesOrderItem, Receipt
from app_inventory.models import LumberProduct, Inventory
from app_inventory.services import InventoryService
from app_sales.notification_models import OrderNotification, OrderConfirmation


class SalesService:
    """Service for managing sales operations"""
    

    @staticmethod
    @transaction.atomic
    def create_sales_order(customer_id, items, payment_type='cash', created_by=None, order_source='point_of_sale'):
        """
        Create a sales order with line items
        
        Args:
            customer_id: Customer ID
            items: List of dicts with 'product_id' and 'quantity_pieces'
            payment_type: 'cash', 'partial', or 'credit'
            created_by: User creating the order
            order_source: 'customer_order' or 'point_of_sale' (default)
            
        Returns:
            SalesOrder: Created sales order
            
        Raises:
            ValidationError: If validation fails
        """
        if not items:
            raise ValidationError("Sales order must have at least one item")
        
        customer = Customer.objects.get(id=customer_id)
        
        # Create sales order without SO number (will generate after)
        so = SalesOrder.objects.create(
            customer=customer,
            payment_type=payment_type,
            created_by=created_by,
            order_source=order_source
        )
        
        # Generate unique SO number
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        prefix = f'SO-{today}-'
        
        # Get count of all orders created today
        count = SalesOrder.objects.filter(
            so_number__startswith=prefix
        ).count() + 1
        
        so.so_number = f'{prefix}{count:04d}'
        so.save()
        
        total_amount = Decimal('0')
        
        # Create line items and deduct stock
        for item_data in items:
            product_id = item_data.get('product_id')
            quantity_pieces = item_data.get('quantity_pieces')
            
            if not product_id or not quantity_pieces:
                raise ValidationError("Each item must have product_id and quantity_pieces")
            
            product = LumberProduct.objects.get(id=product_id)
            
            # Calculate board feet and price
            board_feet = Decimal(str(product.calculate_board_feet(quantity_pieces)))
            unit_price = product.price_per_board_foot
            subtotal = board_feet * unit_price
            
            # Create line item
            SalesOrderItem.objects.create(
                sales_order=so,
                product=product,
                quantity_pieces=quantity_pieces,
                board_feet=board_feet,
                unit_price=unit_price,
                subtotal=subtotal
            )
            
            # Deduct from inventory
            InventoryService.stock_out(
                product_id=product_id,
                quantity_pieces=quantity_pieces,
                reason='sales',
                created_by=created_by,
                reference_id=so.so_number
            )
            
            total_amount += subtotal
        
        # Set total amount
        so.total_amount = total_amount
        
        # Apply discount if eligible
        so.apply_discount()
        
        # Auto-confirm walk-in POS orders (no need for manual confirmation)
        if order_source == 'point_of_sale':
            so.is_confirmed = True
            so.confirmed_at = timezone.now()
            so.confirmed_by = created_by
        
        so.save()
        
        # Create order confirmation
        from datetime import datetime, timedelta
        estimated_pickup_date = (datetime.now() + timedelta(days=3)).date()
        OrderConfirmationService.create_order_confirmation(
            sales_order_id=so.id,
            estimated_pickup_date=estimated_pickup_date,
            created_by=created_by
        )
        
        return so
    

    
    @staticmethod
    def apply_discount(sales_order_id):
        """
        Apply discount to sales order based on customer eligibility
        
        Args:
            sales_order_id: SalesOrder ID
            
        Returns:
            SalesOrder: Updated sales order
        """
        so = SalesOrder.objects.get(id=sales_order_id)
        so.apply_discount()
        so.save()
        return so
    
    @staticmethod
    @transaction.atomic
    def process_payment(sales_order_id, amount_paid, created_by=None):
        """
        Process payment for sales order
        
        Args:
            sales_order_id: SalesOrder ID
            amount_paid: Amount paid by customer (will be ADDED to existing amount_paid)
            created_by: User processing payment
            
        Returns:
            Tuple: (SalesOrder, Receipt)
        """
        so = SalesOrder.objects.get(id=sales_order_id)
        
        # Convert to Decimal
        payment_amount = Decimal(str(amount_paid))
        
        # ADD to existing amount_paid (for partial payments)
        so.amount_paid += payment_amount
        so.balance = so.total_amount - so.discount_amount - so.amount_paid
        
        # Check if payment exceeds balance
        if so.balance < Decimal('-0.01'):
            raise ValidationError("Amount paid exceeds balance")
        
        so.save()
        
        # Create receipt for THIS payment (not total)
        receipt = Receipt.objects.create(
            sales_order=so,
            amount_tendered=payment_amount,
            change=Decimal('0'),  # No change for partial payments
            created_by=created_by
        )
        
        # Generate receipt number
        receipt.receipt_number = SalesService._generate_receipt_number()
        receipt.save()
        
        # Mark payment in confirmation if exists
        try:
            OrderConfirmationService.mark_payment_received(sales_order_id=sales_order_id)
        except:
            pass  # Confirmation might not exist yet
        
        return so, receipt
    
    @staticmethod
    def _generate_receipt_number():
        """Generate unique receipt number"""
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        count = Receipt.objects.filter(receipt_number__startswith=f'RCP-{today}').count() + 1
        return f'RCP-{today}-{count:04d}'
    
    @staticmethod
    def get_customer_account_summary(customer_id):
        """
        Get customer account summary with outstanding balance
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Dict: Customer info, total purchases, outstanding balance
        """
        from django.db.models import Sum, Q
        
        customer = Customer.objects.get(id=customer_id)
        
        sales_orders = SalesOrder.objects.filter(customer=customer)
        
        total_purchases = sales_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        total_paid = sales_orders.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0')
        outstanding_balance = sales_orders.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
        
        # Filter for credit/SOA orders
        credit_orders = sales_orders.filter(payment_type='credit')
        credit_balance = credit_orders.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
        
        return {
            'customer_id': customer.id,
            'customer_name': customer.name,
            'email': customer.email,
            'phone': customer.phone_number,
            'total_purchases': float(total_purchases),
            'total_paid': float(total_paid),
            'outstanding_balance': float(outstanding_balance),
            'credit_balance': float(credit_balance),
            'total_orders': sales_orders.count(),
            'credit_orders': credit_orders.count()
        }
    
    @staticmethod
    def validate_stock_availability(items):
        """
        Validate if sufficient stock is available for items
        
        Args:
            items: List of dicts with 'product_id' and 'quantity_pieces'
            
        Returns:
            Dict: Validation result with product_id, available, requested, valid
        """
        results = []
        all_valid = True
        
        for item_data in items:
            product_id = item_data.get('product_id')
            quantity_pieces = item_data.get('quantity_pieces')
            
            try:
                inventory = Inventory.objects.get(product_id=product_id)
                available = inventory.quantity_pieces
                valid = available >= quantity_pieces
                
                if not valid:
                    all_valid = False
                
                results.append({
                    'product_id': product_id,
                    'available_pieces': available,
                    'requested_pieces': quantity_pieces,
                    'valid': valid
                })
            except Inventory.DoesNotExist:
                all_valid = False
                results.append({
                    'product_id': product_id,
                    'available_pieces': 0,
                    'requested_pieces': quantity_pieces,
                    'valid': False,
                    'error': 'No inventory record'
                })
        
        return {
            'all_valid': all_valid,
            'items': results
        }


class OrderConfirmationService:
    """Service for managing order confirmations and notifications"""
    
    @staticmethod
    @transaction.atomic
    def create_order_confirmation(sales_order_id, estimated_pickup_date=None, created_by=None):
        """
        Create order confirmation after sales order is created
        
        Args:
            sales_order_id: ID of the sales order
            estimated_pickup_date: Date when customer can pick up order
            created_by: User creating the confirmation
            
        Returns:
            OrderConfirmation: Created confirmation record
        """
        sales_order = SalesOrder.objects.get(id=sales_order_id)
        
        # Create confirmation record
        confirmation = OrderConfirmation.objects.create(
            sales_order=sales_order,
            customer=sales_order.customer,
            estimated_pickup_date=estimated_pickup_date,
            created_by=created_by
        )
        
        # Create initial notification
        OrderNotification.objects.create(
            sales_order=sales_order,
            customer=sales_order.customer,
            notification_type='order_confirmed',
            title=f"Order {sales_order.so_number} Confirmed",
            message=f"Your order {sales_order.so_number} has been successfully created. "
                   f"We will notify you when it's ready for pickup."
        )
        
        return confirmation
    
    @staticmethod
    @transaction.atomic
    def confirm_order_ready(sales_order_id):
        """
        Mark order as ready for pickup and notify customer
        
        Args:
            sales_order_id: ID of the sales order
            
        Returns:
            OrderConfirmation: Updated confirmation record
        """
        confirmation = OrderConfirmation.objects.get(sales_order_id=sales_order_id)
        confirmation.mark_ready_for_pickup()
        return confirmation
    
    @staticmethod
    @transaction.atomic
    def mark_payment_received(sales_order_id):
        """
        Mark payment as received for order
        
        Args:
            sales_order_id: ID of the sales order
            
        Returns:
            OrderConfirmation: Updated confirmation record
        """
        confirmation = OrderConfirmation.objects.get(sales_order_id=sales_order_id)
        confirmation.mark_payment_complete()
        return confirmation
    
    @staticmethod
    def get_customer_pending_pickups(customer_id):
        """
        Get all pending pickups for a customer
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            QuerySet: Orders ready for pickup
        """
        return OrderConfirmation.objects.filter(
            customer_id=customer_id,
            status__in=['confirmed', 'ready_for_pickup']
        ).select_related('sales_order').order_by('-ready_at', '-confirmed_at')
    
    @staticmethod
    def get_customer_notifications(customer_id, unread_only=True, limit=20):
        """
        Get notifications for a customer
        
        Args:
            customer_id: ID of the customer
            unread_only: If True, only return unread notifications
            limit: Maximum number of notifications to return
            
        Returns:
            QuerySet: Notifications
        """
        query = OrderNotification.objects.filter(customer_id=customer_id)
        
        if unread_only:
            query = query.filter(is_read=False)
        
        return query.order_by('-created_at')[:limit]
    
    @staticmethod
    @transaction.atomic
    def mark_notification_read(notification_id):
        """
        Mark a notification as read
        
        Args:
            notification_id: ID of the notification
            
        Returns:
            OrderNotification: Updated notification
        """
        notification = OrderNotification.objects.get(id=notification_id)
        notification.mark_as_read()
        return notification
    
    @staticmethod
    @transaction.atomic
    def mark_order_picked_up(sales_order_id):
        """
        Mark order as picked up by customer
        
        Args:
            sales_order_id: ID of the sales order
            
        Returns:
            OrderConfirmation: Updated confirmation record
        """
        confirmation = OrderConfirmation.objects.get(sales_order_id=sales_order_id)
        confirmation.mark_picked_up()
        
        # Create pickup notification
        OrderNotification.objects.create(
            sales_order=confirmation.sales_order,
            customer=confirmation.customer,
            notification_type='order_confirmed',
            title=f"Order {confirmation.sales_order.so_number} Picked Up",
            message=f"Thank you! Your order {confirmation.sales_order.so_number} has been picked up. "
                   f"We appreciate your business!"
        )
        
        return confirmation
