"""
Supplier purchase reports and analytics
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from app_supplier.models import PurchaseOrder, Supplier, SupplierPriceHistory
from app_supplier.serializers import PurchaseOrderSerializer


class SupplierReportViewSet(viewsets.ViewSet):
    """Supplier and purchase reports"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def supplier_totals(self, request):
        """Get total purchases per supplier"""
        suppliers = Supplier.objects.annotate(
            total_amount=Sum('purchase_orders__total_amount'),
            po_count=Count('purchase_orders'),
            avg_po_amount=Avg('purchase_orders__total_amount')
        ).filter(purchase_orders__isnull=False).order_by('-total_amount')
        
        data = []
        for supplier in suppliers:
            data.append({
                'supplier_id': supplier.id,
                'company_name': supplier.company_name,
                'contact_person': supplier.contact_person,
                'total_spent': float(supplier.total_amount or 0),
                'po_count': supplier.po_count,
                'avg_po_amount': float(supplier.avg_po_amount or 0),
                'delivery_rating': float(supplier.delivery_speed_rating)
            })
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def cost_history(self, request):
        """Get cost per board foot history by supplier and product"""
        supplier_id = request.query_params.get('supplier_id')
        product_id = request.query_params.get('product_id')
        
        query = SupplierPriceHistory.objects.select_related('supplier', 'product')
        
        if supplier_id:
            query = query.filter(supplier_id=supplier_id)
        if product_id:
            query = query.filter(product_id=product_id)
        
        query = query.order_by('-valid_from')
        
        data = []
        for history in query:
            data.append({
                'id': history.id,
                'supplier': history.supplier.company_name,
                'product': history.product.name,
                'price_per_unit': float(history.price_per_unit),
                'valid_from': history.valid_from.isoformat(),
                'valid_to': history.valid_to.isoformat() if history.valid_to else None,
            })
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def delivery_performance(self, request):
        """Get supplier delivery performance"""
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timedelta(days=days)
        
        suppliers = Supplier.objects.filter(
            purchase_orders__created_at__gte=cutoff_date
        ).annotate(
            total_pos=Count('purchase_orders'),
            received_pos=Count('purchase_orders', filter=Q(purchase_orders__status='received')),
            pending_pos=Count('purchase_orders', filter=Q(purchase_orders__status='confirmed'))
        )
        
        data = []
        for supplier in suppliers:
            on_time = supplier.received_pos if supplier.delivery_speed_rating >= 4 else supplier.received_pos // 2
            data.append({
                'supplier_id': supplier.id,
                'company_name': supplier.company_name,
                'total_pos': supplier.total_pos,
                'received_pos': supplier.received_pos,
                'pending_pos': supplier.pending_pos,
                'on_time_delivery_estimate': on_time,
                'delivery_rating': float(supplier.delivery_speed_rating)
            })
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def purchase_summary(self, request):
        """Get overall purchase summary"""
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timedelta(days=days)
        
        total_spent = PurchaseOrder.objects.filter(
            created_at__gte=cutoff_date
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        total_pos = PurchaseOrder.objects.filter(
            created_at__gte=cutoff_date
        ).count()
        
        received_pos = PurchaseOrder.objects.filter(
            created_at__gte=cutoff_date,
            status='received'
        ).count()
        
        supplier_count = Supplier.objects.filter(
            purchase_orders__created_at__gte=cutoff_date
        ).distinct().count()
        
        return Response({
            'period_days': days,
            'total_spent': float(total_spent),
            'total_pos': total_pos,
            'received_pos': received_pos,
            'pending_pos': total_pos - received_pos,
            'supplier_count': supplier_count,
            'avg_po_amount': float(total_spent / total_pos) if total_pos > 0 else 0
        })
