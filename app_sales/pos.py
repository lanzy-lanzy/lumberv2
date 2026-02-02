"""
Point of Sale (POS) endpoints for cashiers
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from app_sales.models import Customer, SalesOrder, SalesOrderItem, Receipt
from app_sales.serializers import CustomerSerializer, SalesOrderSerializer, ReceiptSerializer
from app_sales.services import SalesService
from app_inventory.models import LumberProduct


class POSViewSet(viewsets.ViewSet):
    """Point of Sale endpoints for cashiers"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def search_customer(self, request):
        """
        Search for customer by name or phone
        
        Query params:
        - q: Search query (name or phone number)
        """
        query = request.query_params.get('q', '')
        
        if len(query) < 2:
            return Response({'error': 'Query must be at least 2 characters'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        customers = Customer.objects.filter(
            name__icontains=query
        ) | Customer.objects.filter(phone_number__icontains=query)
        
        return Response([{
            'id': c.id,
            'name': c.name,
            'phone': c.phone_number
        } for c in customers[:10]])
    
    @action(detail=False, methods=['get'])
    def search_product(self, request):
        """
        Search for products by name or SKU
        
        Query params:
        - q: Search query (product name or SKU)
        """
        query = request.query_params.get('q', '')
        
        if len(query) < 2:
            return Response({'error': 'Query must be at least 2 characters'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        products = LumberProduct.objects.filter(
            is_active=True
        ).filter(
            name__icontains=query
        ) | LumberProduct.objects.filter(
            is_active=True,
            sku__icontains=query
        )
        
        return Response([{
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'category': str(p.category),
            'dimensions': f"{p.thickness}\" x {p.width}\" x {p.length}ft",
            'board_feet': float(p.board_feet),
            'price_per_bf': float(p.price_per_board_foot),
            'price_per_piece': float(p.price_per_piece) if p.price_per_piece else None
        } for p in products[:10]])
    
    @action(detail=False, methods=['post'])
    def quick_checkout(self, request):
        """
        Quick checkout workflow for POS
        
        Expected payload:
        {
            "customer_id": 1,
            "items": [
                {"product_id": 1, "quantity_pieces": 10},
                {"product_id": 2, "quantity_pieces": 5}
            ],
            "payment_type": "cash",
            "amount_tendered": 1500.00
        }
        """
        customer_id = request.data.get('customer_id')
        items = request.data.get('items', [])
        payment_type = request.data.get('payment_type', 'cash')
        amount_tendered = request.data.get('amount_tendered')
        
        if not customer_id or not items or amount_tendered is None:
            return Response({'error': 'customer_id, items, and amount_tendered are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create sales order
            so = SalesService.create_sales_order(
                customer_id=customer_id,
                items=items,
                payment_type=payment_type,
                created_by=request.user
            )
            
            # Ensure amount_paid does not exceed balance for the purpose of the SO record
            # but we allow amount_tendered to be higher for change calculation.
            order_total = (so.total_amount - so.discount_amount).quantize(Decimal('0.01'))
            amount_tendered_decimal = Decimal(str(amount_tendered)).quantize(Decimal('0.01'))
            amount_to_pay = min(order_total, amount_tendered_decimal)
            
            # Process payment
            so, receipt = SalesService.process_payment(
                sales_order_id=so.id,
                amount_paid=amount_to_pay,
                created_by=request.user
            )
            
            # Update receipt with actual tendered amount if different
            if Decimal(str(amount_tendered)) > amount_to_pay:
                receipt.amount_tendered = Decimal(str(amount_tendered))
                receipt.change = receipt.amount_tendered - order_total
                # Update sales order amount_paid to reflect full tendered amount
                so.amount_paid = receipt.amount_tendered
                so.balance = Decimal('0')  # Fully paid
                receipt.save()
                so.save()

            # Auto-mark as Picked Up for POS transactions (Walk-in)
            try:
                from app_sales.services import OrderConfirmationService
                # First ensure it has a confirmation record (created in create_sales_order)
                # Then mark as ready and picked up
                confirmation = so.confirmation
                confirmation.mark_payment_complete()
                confirmation.mark_ready_for_pickup() 
                confirmation.mark_picked_up()
            except Exception as e:
                # Log error but don't fail transaction
                print(f"Error auto-marking pickup for POS {so.so_number}: {e}")
            
            return Response({
                'status': 'success',
                'sales_order': {
                    'so_number': so.so_number,
                    'customer_name': so.customer.name,
                    'total_amount': float(so.total_amount),
                    'discount_amount': float(so.discount_amount),
                    'amount_paid': float(so.amount_paid),
                    'balance': float(so.balance)
                },
                'receipt': {
                    'receipt_number': receipt.receipt_number,
                    'amount_tendered': float(receipt.amount_tendered),
                    'change': float(receipt.change)
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def daily_report(self, request):
        """Get daily POS report"""
        today = timezone.now().date()
        
        sales_orders = SalesOrder.objects.filter(created_at__date=today)
        receipts = Receipt.objects.filter(created_at__date=today)
        
        payment_summary = sales_orders.values('payment_type').annotate(
            count=Count('id'),
            total_amount=Sum('total_amount'),
            total_discount=Sum('discount_amount'),
            total_paid=Sum('amount_paid')
        )
        
        total_sales = sales_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        total_discount = sales_orders.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0')
        total_paid = sales_orders.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0')
        outstanding = sales_orders.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
        
        return Response({
            'date': today,
            'transactions': {
                'sales_orders': sales_orders.count(),
                'receipts': receipts.count()
            },
            'financial': {
                'total_sales': float(total_sales),
                'total_discount': float(total_discount),
                'total_paid': float(total_paid),
                'outstanding_balance': float(outstanding)
            },
            'by_payment_type': list(payment_summary)
        })
    
    @action(detail=False, methods=['get'])
    def pending_payments(self, request):
        """Get sales orders pending payment"""
        pending = SalesOrder.objects.filter(balance__gt=0).select_related('customer')
        
        return Response([{
            'so_number': so.so_number,
            'customer_id': so.customer.id,
            'customer_name': so.customer.name,
            'total_amount': float(so.total_amount),
            'amount_paid': float(so.amount_paid),
            'balance': float(so.balance),
            'payment_type': so.payment_type,
            'created_at': so.created_at
        } for so in pending[:20]])
    
    @action(detail=False, methods=['post'])
    def void_sale(self, request):
        """
        Void a sales order (reverse transaction)
        
        Expected payload:
        {
            "sales_order_id": 1,
            "reason": "Customer request"
        }
        """
        sales_order_id = request.data.get('sales_order_id')
        reason = request.data.get('reason', 'Voided by cashier')
        
        if not sales_order_id:
            return Response({'error': 'sales_order_id is required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            so = SalesOrder.objects.get(id=sales_order_id)
            
            # Reverse stock deductions
            from app_inventory.services import InventoryService
            for item in so.sales_order_items.all():
                InventoryService.stock_in(
                    product_id=item.product.id,
                    quantity_pieces=item.quantity_pieces,
                    created_by=request.user,
                    reference_id=f"VOID-{so.so_number}"
                )
            
            # Mark as voided (could add a status field to SalesOrder)
            so.notes = f"VOIDED: {reason}"
            so.save()
            
            return Response({
                'status': 'success',
                'message': f'Sales order {so.so_number} has been voided',
                'so_number': so.so_number
            })
        except SalesOrder.DoesNotExist:
            return Response({'error': 'Sales order not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
