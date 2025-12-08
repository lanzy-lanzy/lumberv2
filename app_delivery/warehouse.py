"""
Warehouse management endpoints for staff
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from app_delivery.models import Delivery
from app_delivery.services import DeliveryService


class WarehouseViewSet(viewsets.ViewSet):
    """Warehouse management endpoints"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get warehouse dashboard overview"""
        picking_list = DeliveryService.get_picking_list()
        dispatch_queue = DeliveryService.get_delivery_queue()
        metrics = DeliveryService.get_delivery_metrics()
        
        return Response({
            'metrics': metrics,
            'picking_list': {
                'count': len(picking_list),
                'items': picking_list[:10]  # Show top 10
            },
            'dispatch_queue': {
                'count': len(dispatch_queue),
                'items': dispatch_queue[:10]  # Show top 10
            }
        })
    
    @action(detail=False, methods=['get'])
    def picking_list(self, request):
        """Get detailed picking list for warehouse staff"""
        picking_list = DeliveryService.get_picking_list()
        
        # Allow filtering by status
        status_filter = request.query_params.get('status')
        if status_filter:
            picking_list = [item for item in picking_list if item['status'] == status_filter]
        
        return Response({
            'total_items': len(picking_list),
            'items': picking_list
        })
    
    @action(detail=False, methods=['post'])
    def start_picking(self, request):
        """
        Start picking for a delivery
        
        Expected payload:
        {
            "delivery_id": 1,
            "warehouse_staff_id": 1
        }
        """
        delivery_id = request.data.get('delivery_id')
        
        if not delivery_id:
            return Response({'error': 'delivery_id is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            delivery = DeliveryService.update_status(
                delivery_id=delivery_id,
                new_status='on_picking',
                notes=f'Picking started by {request.user.get_full_name() or request.user.username}',
                updated_by=request.user
            )
            
            return Response({
                'status': 'success',
                'delivery_number': delivery.delivery_number,
                'message': 'Picking started'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def complete_picking(self, request):
        """
        Mark picking as complete and ready for loading
        
        Expected payload:
        {
            "delivery_id": 1
        }
        """
        delivery_id = request.data.get('delivery_id')
        
        if not delivery_id:
            return Response({'error': 'delivery_id is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            delivery = DeliveryService.update_status(
                delivery_id=delivery_id,
                new_status='loaded',
                notes=f'Picking completed by {request.user.get_full_name() or request.user.username}',
                updated_by=request.user
            )
            
            return Response({
                'status': 'success',
                'delivery_number': delivery.delivery_number,
                'message': 'Items loaded and ready for dispatch'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def dispatch_queue(self, request):
        """Get dispatch queue (items ready to ship)"""
        queue = DeliveryService.get_delivery_queue()
        
        # Filter by status if requested
        status_filter = request.query_params.get('status')
        if status_filter:
            queue = [item for item in queue if item['status'] == status_filter]
        
        return Response({
            'total_items': len(queue),
            'items': queue
        })
    
    @action(detail=False, methods=['post'])
    def assign_driver(self, request):
        """
        Assign driver and vehicle to delivery
        
        Expected payload:
        {
            "delivery_id": 1,
            "driver_name": "John Doe",
            "plate_number": "ABC-1234"
        }
        """
        delivery_id = request.data.get('delivery_id')
        driver_name = request.data.get('driver_name')
        plate_number = request.data.get('plate_number')
        
        if not delivery_id or not driver_name or not plate_number:
            return Response({
                'error': 'delivery_id, driver_name, and plate_number are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            delivery = DeliveryService.update_status(
                delivery_id=delivery_id,
                new_status='out_for_delivery',
                driver_name=driver_name,
                plate_number=plate_number,
                notes=f'Assigned to {driver_name} ({plate_number})',
                updated_by=request.user
            )
            
            return Response({
                'status': 'success',
                'delivery_number': delivery.delivery_number,
                'driver_name': delivery.driver_name,
                'plate_number': delivery.plate_number,
                'message': 'Driver and vehicle assigned'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_status_change(self, request):
        """
        Bulk change status for multiple deliveries
        
        Expected payload:
        {
            "delivery_ids": [1, 2, 3],
            "status": "on_picking"
        }
        """
        delivery_ids = request.data.get('delivery_ids', [])
        new_status = request.data.get('status')
        
        if not delivery_ids or not new_status:
            return Response({
                'error': 'delivery_ids and status are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = DeliveryService.bulk_update_status(
            delivery_ids=delivery_ids,
            new_status=new_status,
            notes=f'Bulk updated by {request.user.get_full_name() or request.user.username}',
            updated_by=request.user
        )
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def stuck_deliveries(self, request):
        """Get deliveries stuck in process for too long"""
        from datetime import timedelta
        from django.utils import timezone
        
        hours = int(request.query_params.get('hours', 24))
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        stuck = Delivery.objects.filter(
            status__in=['pending', 'on_picking', 'loaded', 'out_for_delivery'],
            created_at__lte=cutoff_time
        ).select_related('sales_order', 'sales_order__customer').order_by('created_at')
        
        items = []
        for delivery in stuck:
            age_hours = (timezone.now() - delivery.created_at).total_seconds() / 3600
            so = delivery.sales_order
            
            items.append({
                'delivery_id': delivery.id,
                'delivery_number': delivery.delivery_number,
                'so_number': so.so_number,
                'customer': so.customer.name,
                'customer_phone': so.customer.phone_number,
                'status': delivery.status,
                'age_hours': round(age_hours, 1),
                'created_at': delivery.created_at
            })
        
        return Response({
            'threshold_hours': hours,
            'stuck_count': len(items),
            'deliveries': items
        })
