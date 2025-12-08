"""
Delivery management services
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime
from app_delivery.models import Delivery, DeliveryLog
from app_sales.models import SalesOrder


class DeliveryService:
    """Service for managing deliveries"""
    
    # Valid status transitions
    VALID_TRANSITIONS = {
        'pending': ['on_picking', 'cancelled'],
        'on_picking': ['loaded', 'pending'],
        'loaded': ['out_for_delivery', 'pending'],
        'out_for_delivery': ['delivered', 'pending'],
        'delivered': [],
        'cancelled': []
    }
    
    @staticmethod
    @transaction.atomic
    def create_delivery_from_order(sales_order_id, created_by=None):
        """
        Create delivery request from sales order
        
        Args:
            sales_order_id: SalesOrder ID
            created_by: User creating the delivery
            
        Returns:
            Delivery: Created delivery
            
        Raises:
            ValidationError: If delivery already exists or SO not found
        """
        so = SalesOrder.objects.get(id=sales_order_id)
        
        # Check if delivery already exists
        if hasattr(so, 'delivery'):
            raise ValidationError(f"Delivery already exists for {so.so_number}")
        
        # Create delivery
        delivery = Delivery.objects.create(
            sales_order=so,
            status='pending'
        )
        
        # Generate delivery number
        delivery.delivery_number = DeliveryService._generate_delivery_number()
        delivery.save()
        
        # Create initial log entry
        DeliveryLog.objects.create(
            delivery=delivery,
            status='pending',
            notes=f'Delivery created from {so.so_number}',
            updated_by=created_by
        )
        
        return delivery
    
    @staticmethod
    def _generate_delivery_number():
        """Generate unique delivery number"""
        today = datetime.now().strftime('%Y%m%d')
        count = Delivery.objects.filter(delivery_number__startswith=f'DLV-{today}').count() + 1
        return f'DLV-{today}-{count:04d}'
    
    @staticmethod
    @transaction.atomic
    def update_status(delivery_id, new_status, notes='', updated_by=None, driver_name=None, plate_number=None, signature=None):
        """
        Update delivery status with validation
        
        Args:
            delivery_id: Delivery ID
            new_status: New status
            notes: Status change notes
            updated_by: User updating
            driver_name: Driver name (for out_for_delivery)
            plate_number: Vehicle plate (for out_for_delivery)
            signature: Customer signature (for delivered)
            
        Returns:
            Delivery: Updated delivery
            
        Raises:
            ValidationError: If transition is invalid
        """
        delivery = Delivery.objects.get(id=delivery_id)
        current_status = delivery.status
        
        # Validate transition
        valid_next = DeliveryService.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in valid_next:
            raise ValidationError(
                f"Invalid status transition from {current_status} to {new_status}. "
                f"Valid options: {', '.join(valid_next)}"
            )
        
        # Update status and related fields
        delivery.status = new_status
        
        if new_status == 'out_for_delivery':
            if driver_name:
                delivery.driver_name = driver_name
            if plate_number:
                delivery.plate_number = plate_number
        
        if new_status == 'delivered':
            delivery.delivered_at = timezone.now()
            if signature:
                delivery.customer_signature = signature
        
        delivery.updated_at = timezone.now()
        delivery.save()
        
        # Create log entry
        DeliveryLog.objects.create(
            delivery=delivery,
            status=new_status,
            notes=notes,
            updated_by=updated_by
        )
        
        return delivery
    
    @staticmethod
    def get_picking_list(status_filter='pending'):
        """
        Get picking list for warehouse staff
        
        Args:
            status_filter: Filter by delivery status
            
        Returns:
            List of deliveries with items to pick
        """
        if status_filter not in ['pending', 'on_picking']:
            status_filter = 'pending'
        
        deliveries = Delivery.objects.filter(
            status__in=['pending', 'on_picking']
        ).select_related('sales_order', 'sales_order__customer').prefetch_related(
            'sales_order__sales_order_items'
        ).order_by('created_at')
        
        picking_list = []
        for delivery in deliveries:
            so = delivery.sales_order
            picking_list.append({
                'delivery_id': delivery.id,
                'delivery_number': delivery.delivery_number,
                'so_number': so.so_number,
                'customer_name': so.customer.name,
                'customer_phone': so.customer.phone_number,
                'customer_address': so.customer.address,
                'status': delivery.status,
                'items': [
                    {
                        'product_id': item.product.id,
                        'product_name': item.product.name,
                        'sku': item.product.sku,
                        'quantity_pieces': item.quantity_pieces,
                        'board_feet': float(item.board_feet),
                        'dimensions': f"{item.product.thickness}\" x {item.product.width}\" x {item.product.length}ft"
                    }
                    for item in so.sales_order_items.all()
                ],
                'created_at': delivery.created_at,
                'priority': 1 if delivery.status == 'on_picking' else 0  # Priority to in-progress
            })
        
        # Sort by priority and creation date
        picking_list.sort(key=lambda x: (-x['priority'], x['created_at']))
        return picking_list
    
    @staticmethod
    def get_delivery_queue():
        """
        Get delivery queue for dispatch
        
        Returns:
            List of ready-to-dispatch deliveries
        """
        deliveries = Delivery.objects.filter(
            status__in=['loaded', 'out_for_delivery']
        ).select_related('sales_order', 'sales_order__customer').order_by('status', 'created_at')
        
        queue = []
        for delivery in deliveries:
            so = delivery.sales_order
            queue.append({
                'delivery_id': delivery.id,
                'delivery_number': delivery.delivery_number,
                'so_number': so.so_number,
                'customer_name': so.customer.name,
                'customer_phone': so.customer.phone_number,
                'customer_address': so.customer.address,
                'status': delivery.status,
                'driver_name': delivery.driver_name or 'Not assigned',
                'plate_number': delivery.plate_number or 'Not assigned',
                'total_items': so.sales_order_items.count(),
                'total_bf': float(sum(item.board_feet for item in so.sales_order_items.all())),
                'created_at': delivery.created_at
            })
        
        return queue
    
    @staticmethod
    def get_delivery_metrics():
        """
        Get delivery metrics summary
        
        Returns:
            Dict with delivery KPIs
        """
        from django.db.models import Count, Q, Avg
        from datetime import timedelta
        
        total = Delivery.objects.count()
        pending = Delivery.objects.filter(status='pending').count()
        on_picking = Delivery.objects.filter(status='on_picking').count()
        loaded = Delivery.objects.filter(status='loaded').count()
        in_transit = Delivery.objects.filter(status='out_for_delivery').count()
        delivered = Delivery.objects.filter(status='delivered').count()
        
        # Calculate average delivery time
        delivered_with_time = Delivery.objects.filter(
            status='delivered',
            delivered_at__isnull=False
        ).annotate(
            delivery_time=(
                Delivery._meta.get_field('delivered_at').get_prep_value
            )
        )
        
        # Simpler approach: get last 7 days delivered
        recent_delivered = Delivery.objects.filter(
            status='delivered',
            delivered_at__gte=timezone.now() - timedelta(days=7)
        )
        
        avg_time_hours = 0
        if recent_delivered.exists():
            total_time = sum((d.delivered_at - d.created_at).total_seconds() 
                           for d in recent_delivered if d.delivered_at)
            avg_time_hours = (total_time / len(recent_delivered)) / 3600 if recent_delivered.count() > 0 else 0
        
        return {
            'total_deliveries': total,
            'pending': pending,
            'on_picking': on_picking,
            'loaded': loaded,
            'in_transit': in_transit,
            'delivered': delivered,
            'avg_delivery_time_hours': round(avg_time_hours, 1),
            'completion_rate': round((delivered / total * 100), 1) if total > 0 else 0
        }
    
    @staticmethod
    def bulk_update_status(delivery_ids, new_status, notes='', updated_by=None):
        """
        Bulk update delivery status
        
        Args:
            delivery_ids: List of delivery IDs
            new_status: New status for all
            notes: Status change notes
            updated_by: User updating
            
        Returns:
            Dict with success/failure counts
        """
        success_count = 0
        failed_count = 0
        errors = []
        
        for delivery_id in delivery_ids:
            try:
                DeliveryService.update_status(
                    delivery_id=delivery_id,
                    new_status=new_status,
                    notes=notes,
                    updated_by=updated_by
                )
                success_count += 1
            except ValidationError as e:
                failed_count += 1
                errors.append(f"Delivery {delivery_id}: {str(e)}")
            except Exception as e:
                failed_count += 1
                errors.append(f"Delivery {delivery_id}: {str(e)}")
        
        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }
