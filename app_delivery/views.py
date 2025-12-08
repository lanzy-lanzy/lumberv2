from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime
from app_delivery.models import Delivery, DeliveryLog
from app_delivery.serializers import DeliverySerializer, DeliveryLogSerializer
from app_delivery.services import DeliveryService


class DeliveryViewSet(viewsets.ModelViewSet):
    """API endpoint for deliveries"""
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def create_from_order(self, request):
        """
        Create delivery from sales order
        
        Expected payload:
        {
            "sales_order_id": 1
        }
        """
        sales_order_id = request.data.get('sales_order_id')
        
        if not sales_order_id:
            return Response({'error': 'sales_order_id is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            delivery = DeliveryService.create_delivery_from_order(
                sales_order_id=sales_order_id,
                created_by=request.user
            )
            serializer = self.get_serializer(delivery)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update delivery status with validation
        
        Expected payload:
        {
            "status": "loaded",
            "notes": "Items loaded on truck",
            "driver_name": "John Doe",
            "plate_number": "ABC-1234",
            "signature": "Customer signature"
        }
        """
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        driver_name = request.data.get('driver_name')
        plate_number = request.data.get('plate_number')
        signature = request.data.get('signature')
        
        if not new_status:
            return Response({'error': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            delivery = DeliveryService.update_status(
                delivery_id=pk,
                new_status=new_status,
                notes=notes,
                updated_by=request.user,
                driver_name=driver_name,
                plate_number=plate_number,
                signature=signature
            )
            serializer = self.get_serializer(delivery)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Get deliveries by status"""
        delivery_status = request.query_params.get('status')
        if not delivery_status:
            return Response({'error': 'status parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        deliveries = Delivery.objects.filter(status=delivery_status)
        serializer = self.get_serializer(deliveries, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending deliveries (not yet delivered)"""
        deliveries = Delivery.objects.filter(status__in=['pending', 'on_picking', 'loaded', 'out_for_delivery'])
        serializer = self.get_serializer(deliveries, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def picking_list(self, request):
        """Get warehouse picking list"""
        picking_list = DeliveryService.get_picking_list()
        return Response({
            'count': len(picking_list),
            'items': picking_list
        })
    
    @action(detail=False, methods=['get'])
    def dispatch_queue(self, request):
        """Get dispatch queue for loaded/out-for-delivery items"""
        queue = DeliveryService.get_delivery_queue()
        return Response({
            'count': len(queue),
            'queue': queue
        })
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """Get delivery metrics and KPIs"""
        metrics = DeliveryService.get_delivery_metrics()
        return Response(metrics)
    
    @action(detail=False, methods=['post'])
    def bulk_status_update(self, request):
        """
        Bulk update delivery status
        
        Expected payload:
        {
            "delivery_ids": [1, 2, 3],
            "status": "on_picking",
            "notes": "Started picking process"
        }
        """
        delivery_ids = request.data.get('delivery_ids', [])
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if not delivery_ids or not new_status:
            return Response({'error': 'delivery_ids and status are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        result = DeliveryService.bulk_update_status(
            delivery_ids=delivery_ids,
            new_status=new_status,
            notes=notes,
            updated_by=request.user
        )
        
        return Response(result)
