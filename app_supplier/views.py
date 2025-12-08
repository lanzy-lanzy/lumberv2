from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime
from app_supplier.models import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierPriceHistory
from app_supplier.serializers import (
    SupplierSerializer, PurchaseOrderSerializer, 
    PurchaseOrderItemSerializer, SupplierPriceHistorySerializer
)
from app_inventory.services import InventoryService


class SupplierViewSet(viewsets.ModelViewSet):
    """API endpoint for suppliers"""
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get supplier performance metrics"""
        supplier = self.get_object()
        from django.db.models import Count, Avg, Q
        from django.utils import timezone
        from datetime import timedelta
        
        # Get last 30 days of POs
        cutoff_date = timezone.now() - timedelta(days=30)
        recent_pos = supplier.purchase_orders.filter(created_at__gte=cutoff_date)
        
        metrics = {
            'supplier_id': supplier.id,
            'company_name': supplier.company_name,
            'total_pos': supplier.purchase_orders.count(),
            'recent_pos_30days': recent_pos.count(),
            'received_pos': recent_pos.filter(status='received').count(),
            'average_delivery_rating': supplier.delivery_speed_rating,
            'total_spent': sum(po.total_amount for po in supplier.purchase_orders.all()),
            'price_history_count': supplier.price_history.count()
        }
        
        return Response(metrics)
    
    @action(detail=False, methods=['get'])
    def top_suppliers(self, request):
        """Get top suppliers by total purchase amount"""
        from django.db.models import Sum
        
        limit = int(request.query_params.get('limit', 5))
        suppliers = Supplier.objects.annotate(
            total_spent=Sum('purchase_orders__total_amount')
        ).order_by('-total_spent')[:limit]
        
        serializer = self.get_serializer(suppliers, many=True)
        return Response(serializer.data)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """API endpoint for purchase orders"""
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        po = serializer.save(created_by=self.request.user)
        po.po_number = self._generate_po_number()
        po.save()
    
    def _generate_po_number(self):
        """Generate unique purchase order number"""
        today = datetime.now().strftime('%Y%m%d')
        count = PurchaseOrder.objects.filter(po_number__startswith=f'PO-{today}').count() + 1
        return f'PO-{today}-{count:04d}'
    
    @action(detail=True, methods=['post'])
    def mark_received(self, request, pk=None):
        """Mark purchase order as received and auto-convert to stock in"""
        po = self.get_object()
        
        if po.status != 'confirmed':
            return Response({'error': 'Only confirmed POs can be marked as received'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Auto-convert PO items to stock in
            for po_item in po.po_items.all():
                InventoryService.stock_in(
                    product_id=po_item.product_id,
                    quantity_pieces=po_item.quantity_pieces,
                    supplier_id=po.supplier_id,
                    cost_per_unit=po_item.cost_per_unit,
                    created_by=request.user,
                    reference_id=po.po_number
                )
            
            po.status = 'received'
            po.received_at = timezone.now()
            po.save()
            
            serializer = self.get_serializer(po)
            return Response({
                'message': f'PO {po.po_number} marked as received and stock in created',
                'data': serializer.data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_supplier(self, request):
        """Get purchase orders by supplier"""
        supplier_id = request.query_params.get('supplier_id')
        if not supplier_id:
            return Response({'error': 'supplier_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        orders = PurchaseOrder.objects.filter(supplier_id=supplier_id)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Get purchase orders by status"""
        po_status = request.query_params.get('status')
        if not po_status:
            return Response({'error': 'status parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        orders = PurchaseOrder.objects.filter(status=po_status)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit a draft PO to supplier"""
        po = self.get_object()
        
        if po.status != 'draft':
            return Response({'error': 'Only draft POs can be submitted'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        po.status = 'submitted'
        po.save()
        
        serializer = self.get_serializer(po)
        return Response({'message': f'PO {po.po_number} submitted', 'data': serializer.data})
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a submitted PO"""
        po = self.get_object()
        
        if po.status != 'submitted':
            return Response({'error': 'Only submitted POs can be confirmed'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        po.status = 'confirmed'
        po.save()
        
        serializer = self.get_serializer(po)
        return Response({'message': f'PO {po.po_number} confirmed', 'data': serializer.data})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a PO"""
        po = self.get_object()
        
        if po.status == 'received':
            return Response({'error': 'Cannot cancel a received PO'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        po.status = 'cancelled'
        po.save()
        
        serializer = self.get_serializer(po)
        return Response({'message': f'PO {po.po_number} cancelled', 'data': serializer.data})


class SupplierPriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for supplier price history (read-only)"""
    queryset = SupplierPriceHistory.objects.all()
    serializer_class = SupplierPriceHistorySerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def current_prices(self, request):
        """Get current prices for a supplier and product"""
        supplier_id = request.query_params.get('supplier_id')
        product_id = request.query_params.get('product_id')
        
        query = SupplierPriceHistory.objects.filter(valid_to__isnull=True)
        
        if supplier_id:
            query = query.filter(supplier_id=supplier_id)
        if product_id:
            query = query.filter(product_id=product_id)
        
        serializer = self.get_serializer(query, many=True)
        return Response(serializer.data)
