from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from decimal import Decimal
from app_sales.models import Customer, SalesOrder, SalesOrderItem, Receipt
from app_sales.serializers import CustomerSerializer, SalesOrderSerializer, SalesOrderItemSerializer, ReceiptSerializer
from app_sales.services import SalesService, OrderConfirmationService


class CustomerViewSet(viewsets.ModelViewSet):
    """API endpoint for customers"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def account_summary(self, request, pk=None):
        """Get customer account summary"""
        summary = SalesService.get_customer_account_summary(pk)
        return Response(summary)
    

class SalesOrderViewSet(viewsets.ModelViewSet):
    """API endpoint for sales orders"""
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        """Override update to prevent editing confirmed orders"""
        instance = self.get_object()
        if instance.is_confirmed:
            return Response(
                {'error': 'Cannot edit a confirmed order. Please contact administrator if changes are needed.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Override partial_update to prevent editing confirmed orders"""
        instance = self.get_object()
        if instance.is_confirmed:
            return Response(
                {'error': 'Cannot edit a confirmed order. Please contact administrator if changes are needed.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def confirm_order(self, request, pk=None):
        """
        Confirm a sales order (admin only) - prevents further edits and notifies customer
        """
        try:
            order = self.get_object()
            
            # Check if already confirmed
            if order.is_confirmed:
                return Response(
                    {'error': 'Order is already confirmed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Confirm the order
            # The signal will automatically call confirmation.mark_ready_for_pickup()
            # which creates the notification and updates the confirmation status
            order.is_confirmed = True
            order.confirmed_at = timezone.now()
            order.confirmed_by = request.user
            order.save()
            
            serializer = self.get_serializer(order)
            return Response({
                'message': 'Order confirmed successfully. Customer has been notified.',
                'order': serializer.data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def create_order(self, request):
        """
        Create a sales order with automatic stock deduction
        
        Expected payload:
        {
            "customer_id": 1,
            "payment_type": "cash",
            "items": [
                {"product_id": 1, "quantity_pieces": 10},
                {"product_id": 2, "quantity_pieces": 5}
            ]
        }
        """
        customer_id = request.data.get('customer_id')
        items = request.data.get('items', [])
        payment_type = request.data.get('payment_type', 'cash')
        
        if not customer_id or not items:
            return Response({'error': 'customer_id and items are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            so = SalesService.create_sales_order(
                customer_id=customer_id,
                items=items,
                payment_type=payment_type,
                created_by=request.user
            )
            serializer = self.get_serializer(so)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def validate_stock(self, request):
        """
        Validate if stock is available for items before creating order
        
        Expected payload:
        {
            "items": [
                {"product_id": 1, "quantity_pieces": 10},
                {"product_id": 2, "quantity_pieces": 5}
            ]
        }
        """
        items = request.data.get('items', [])
        
        if not items:
            return Response({'error': 'items are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        validation = SalesService.validate_stock_availability(items)
        return Response(validation)
    
    @action(detail=True, methods=['post'])
    def apply_discount(self, request, pk=None):
        """Apply/recalculate discount for sales order"""
        try:
            so = SalesService.apply_discount(pk)
            serializer = self.get_serializer(so)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_customer(self, request):
        """Get sales orders by customer"""
        customer_id = request.query_params.get('customer_id')
        if not customer_id:
            return Response({'error': 'customer_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        orders = SalesOrder.objects.filter(customer_id=customer_id)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today_sales(self, request):
        """Get today's sales"""
        today = timezone.now().date()
        orders = SalesOrder.objects.filter(created_at__date=today)
        
        total = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        
        return Response({
            'date': today,
            'count': orders.count(),
            'total_amount': float(total),
            'orders': self.get_serializer(orders, many=True).data
        })
    
    @action(detail=False, methods=['get'])
    def payment_type_summary(self, request):
        """Get sales summary by payment type"""
        today = timezone.now().date()
        orders = SalesOrder.objects.filter(created_at__date=today)
        
        summary = orders.values('payment_type').annotate(
            count=Count('id'),
            total=Sum('total_amount'),
            paid=Sum('amount_paid')
        )
        
        return Response(list(summary))


class ReceiptViewSet(viewsets.ModelViewSet):
    """API endpoint for receipts"""
    queryset = Receipt.objects.all()
    serializer_class = ReceiptSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def process_payment(self, request):
        """
        Process payment and generate receipt
        
        Expected payload:
        {
            "sales_order_id": 1,
            "amount_paid": 1500.00
        }
        """
        sales_order_id = request.data.get('sales_order_id')
        amount_paid = request.data.get('amount_paid')
        
        if not sales_order_id or amount_paid is None:
            return Response({'error': 'sales_order_id and amount_paid are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            so, receipt = SalesService.process_payment(
                sales_order_id=sales_order_id,
                amount_paid=amount_paid,
                created_by=request.user
            )
            
            return Response({
                'sales_order': SalesOrderSerializer(so).data,
                'receipt': ReceiptSerializer(receipt).data
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def today_receipts(self, request):
        """Get today's receipts"""
        today = timezone.now().date()
        receipts = Receipt.objects.filter(created_at__date=today)
        
        total = receipts.aggregate(Sum('sales_order__total_amount'))['sales_order__total_amount__sum'] or Decimal('0')
        
        return Response({
            'date': today,
            'count': receipts.count(),
            'total_sales': float(total),
            'receipts': self.get_serializer(receipts, many=True).data
        })
    
    @action(detail=False, methods=['get'])
    def by_sales_order(self, request):
        """Get receipt for a specific sales order"""
        so_id = request.query_params.get('sales_order_id')
        if not so_id:
            return Response({'error': 'sales_order_id parameter required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            receipt = Receipt.objects.get(sales_order_id=so_id)
            serializer = self.get_serializer(receipt)
            return Response(serializer.data)
        except Receipt.DoesNotExist:
            return Response({'error': 'Receipt not found'}, status=status.HTTP_404_NOT_FOUND)
