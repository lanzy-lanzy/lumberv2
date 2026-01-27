from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q, F, Avg
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from datetime import timedelta
import json
from app_dashboard.models import DashboardMetric
from app_dashboard.serializers import DashboardMetricSerializer
from app_dashboard.reporting import ComprehensiveReports
from app_inventory.models import Inventory, StockTransaction, LumberProduct
from app_inventory.services import InventoryService
from app_sales.models import SalesOrder
from app_delivery.models import Delivery


class DashboardMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for dashboard metrics"""
    queryset = DashboardMetric.objects.all()
    serializer_class = DashboardMetricSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def inventory_summary(self, request):
        """Get inventory summary metrics"""
        total_bf = Inventory.objects.aggregate(total=Sum('total_board_feet'))['total'] or 0
        total_products = LumberProduct.objects.filter(is_active=True).count()
        
        return Response({
            'total_board_feet': float(total_bf),
            'total_products': total_products,
            'products_with_inventory': Inventory.objects.filter(quantity_pieces__gt=0).count()
        })
    
    @action(detail=False, methods=['get'])
    def sales_summary(self, request):
        """Get sales summary metrics"""
        today = timezone.now().date()
        
        daily_sales = SalesOrder.objects.filter(created_at__date=today).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        return Response({
            'daily_sales_amount': float(daily_sales['total'] or 0),
            'daily_sales_count': daily_sales['count'],
        })
    
    @action(detail=False, methods=['get'])
    def delivery_summary(self, request):
        """Get delivery summary metrics"""
        pending = Delivery.objects.filter(status__in=['pending', 'on_picking', 'loaded']).count()
        in_transit = Delivery.objects.filter(status='out_for_delivery').count()
        delivered = Delivery.objects.filter(status='delivered').count()
        
        return Response({
            'pending': pending,
            'in_transit': in_transit,
            'delivered': delivered,
        })
    
    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        """Get products with low stock"""
        threshold = request.query_params.get('threshold', 100)
        low_stock = InventoryService.get_low_stock_products(float(threshold))
        
        return Response({
            'low_stock_count': low_stock.count(),
            'threshold': float(threshold),
            'products': [
                {
                    'product_id': inv.product.id,
                    'product_name': inv.product.name,
                    'sku': inv.product.sku,
                    'category': inv.product.get_category_display() if hasattr(inv.product, 'get_category_display') else str(inv.product.category),
                    'current_pieces': inv.quantity_pieces,
                    'current_bf': float(inv.total_board_feet),
                    'price_per_bf': float(inv.product.price_per_board_foot)
                }
                for inv in low_stock
            ]
        })
    
    @action(detail=False, methods=['get'])
    def fast_moving_items(self, request):
        """Get fast-moving items (high volume sales)"""
        days = int(request.query_params.get('days', 30))
        min_transactions = int(request.query_params.get('min_transactions', 5))
        
        products = InventoryService.get_fast_moving_items(days=days, min_transactions=min_transactions)
        
        return Response({
            'period_days': days,
            'min_transactions': min_transactions,
            'items': list(products)
        })
    
    @action(detail=False, methods=['get'])
    def overstock_alert(self, request):
        """Get overstocked items"""
        max_bf = float(request.query_params.get('max_bf', 5000))
        overstock = InventoryService.get_overstock_products(max_bf=max_bf)
        
        return Response({
            'overstock_threshold': max_bf,
            'overstock_count': overstock.count(),
            'products': [
                {
                    'product_id': inv.product.id,
                    'product_name': inv.product.name,
                    'sku': inv.product.sku,
                    'current_pieces': inv.quantity_pieces,
                    'current_bf': float(inv.total_board_feet),
                    'value': float(inv.total_board_feet * inv.product.price_per_board_foot)
                }
                for inv in overstock
            ]
        })
    
    @action(detail=False, methods=['get'])
    def price_monitor(self, request):
        """Monitor price changes"""
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get all products with price changes in the period
        price_changes = StockTransaction.objects.filter(
            transaction_type='stock_in',
            created_at__gte=cutoff_date,
            cost_per_unit__isnull=False
        ).values('product__id', 'product__name', 'product__sku').annotate(
            min_cost=F('cost_per_unit'),
            max_cost=F('cost_per_unit'),
            avg_cost=Avg('cost_per_unit')
        ).order_by('product__id').distinct()
        
        return Response({
            'period_days': days,
            'changes': list(price_changes)
        })
    
    @action(detail=False, methods=['get'])
    def full_inventory_report(self, request):
        """Get comprehensive inventory report"""
        all_inventory = Inventory.objects.all().select_related('product')
        
        total_value = sum(float(inv.total_board_feet * inv.product.price_per_board_foot) for inv in all_inventory)
        
        return Response({
            'total_items': all_inventory.count(),
            'total_pieces': sum(inv.quantity_pieces for inv in all_inventory),
            'total_board_feet': sum(float(inv.total_board_feet) for inv in all_inventory),
            'total_inventory_value': total_value,
            'products': [
                {
                    'product_id': inv.product.id,
                    'product_name': inv.product.name,
                    'sku': inv.product.sku,
                    'pieces': inv.quantity_pieces,
                    'board_feet': float(inv.total_board_feet),
                    'price_per_bf': float(inv.product.price_per_board_foot),
                    'total_value': float(inv.total_board_feet * inv.product.price_per_board_foot)
                }
                for inv in all_inventory.order_by('product__name')
            ]
        })
    
    @action(detail=False, methods=['get'])
    def executive_dashboard(self, request):
        """Get executive summary dashboard"""
        days = int(request.query_params.get('days', 30))
        report = ComprehensiveReports.executive_summary(days=days)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def low_stock_alerts_comprehensive(self, request):
        """Get all low stock alerts"""
        alerts = ComprehensiveReports.low_stock_alert()
        return Response({
            'count': len(alerts),
            'alerts': alerts
        })
    
    @action(detail=False, methods=['get'])
    def overstock_alerts_comprehensive(self, request):
        """Get all overstock alerts"""
        threshold = int(request.query_params.get('threshold', 5000))
        alerts = ComprehensiveReports.overstock_alert(threshold_bf=threshold)
        return Response({
            'threshold': threshold,
            'count': len(alerts),
            'alerts': alerts
        })
    
    @action(detail=False, methods=['get'])
    def aged_receivables(self, request):
        """Get aged receivables (credit/SOA accounts)"""
        days = int(request.query_params.get('days', 30))
        report = ComprehensiveReports.aged_receivables(days_threshold=days)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def product_performance(self, request):
        """Get product performance metrics"""
        days = int(request.query_params.get('days', 30))
        products = ComprehensiveReports.product_performance(days=days)
        return Response({
            'period_days': days,
            'products': products
        })
    
    @action(detail=False, methods=['get'])
    def category_performance(self, request):
        """Get category performance metrics"""
        days = int(request.query_params.get('days', 30))
        categories = ComprehensiveReports.category_performance(days=days)
        return Response({
            'period_days': days,
            'categories': categories
        })
    
    @action(detail=False, methods=['get'])
    def cash_flow(self, request):
        """Get cash flow summary"""
        days = int(request.query_params.get('days', 30))
        report = ComprehensiveReports.cash_flow_summary(days=days)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def supplier_analysis(self, request):
        """Get supplier performance analysis"""
        days = int(request.query_params.get('days', 30))
        suppliers = ComprehensiveReports.supplier_analysis(days=days)
        return Response({
            'period_days': days,
            'suppliers': suppliers
        })
    
    @action(detail=False, methods=['get'])
    def inventory_composition(self, request):
        """Get inventory composition by category"""
        report = ComprehensiveReports.inventory_composition()
        return Response(report)


# HTML Views for Dashboard Partials
@login_required
def low_stock_alerts_view(request):
    """Render low stock alerts as HTML"""
    alerts = ComprehensiveReports.low_stock_alert()
    return render(request, 'partials/low_stock_alerts_partial.html', {'alerts': alerts})


@login_required
def aged_receivables_view(request):
    """Render aged receivables as HTML"""
    days = int(request.GET.get('days', 30))
    data = ComprehensiveReports.aged_receivables(days_threshold=days)
    return render(request, 'partials/aged_receivables_partial.html', data)


@login_required
def inventory_composition_view(request):
    """Render inventory composition as HTML"""
    data = ComprehensiveReports.inventory_composition()
    # Ensure all data is JSON-serializable by converting to floats
    categories = {k: {
        'value': v['value'],
        'board_feet': v['board_feet'],
        'product_count': v['product_count'],
        'percentage_of_total': v['percentage_of_total'],
        'products': v['products']
    } for k, v in data['categories'].items()}
    
    context = {
        'total_inventory_value': data['total_inventory_value'],
        'total_board_feet': data['total_board_feet'],
        'categories': json.dumps(categories, cls=DjangoJSONEncoder)
    }
    return render(request, 'partials/inventory_composition_partial.html', context)


@login_required
def sales_trend_view(request):
    """Render sales trend as HTML"""
    days = int(request.GET.get('days', 30))
    cutoff_date = timezone.now() - timedelta(days=days)
    
    sales_data = SalesOrder.objects.filter(
        created_at__gte=cutoff_date
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('total_amount'),
        count=Count('id'),
        avg=Avg('total_amount')
    ).order_by('date')
    
    # Convert data to JSON-serializable format
    data = []
    for item in sales_data:
        data.append({
            'date': item['date'].isoformat() if item['date'] else None,
            'total': float(item['total'] or 0),
            'count': item['count'],
            'avg': float(item['avg'] or 0)
        })
    
    # Serialize as JSON string
    data_json = json.dumps(data, cls=DjangoJSONEncoder)
    return render(request, 'partials/sales_trend_partial.html', {'data': data_json})


@login_required
def supplier_totals_view(request):
    """Render supplier totals as HTML"""
    days = int(request.GET.get('days', 30))
    suppliers = ComprehensiveReports.supplier_analysis(days=days)
    return render(request, 'partials/supplier_totals_partial.html', {'suppliers': suppliers})
