"""
Inventory reporting and analytics
"""
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from app_inventory.models import Inventory, StockTransaction, InventorySnapshot, LumberProduct
from app_sales.models import SalesOrder, SalesOrderItem


class InventoryReports:
    """Generate inventory reports"""
    
    @staticmethod
    def monthly_usage_vs_purchases(year, month):
        """
        Compare monthly usage vs purchases
        
        Args:
            year: Year (2024)
            month: Month (1-12)
            
        Returns:
            Dict with usage and purchase data
        """
        from datetime import date
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        purchases = StockTransaction.objects.filter(
            transaction_type='stock_in',
            created_at__gte=start_date,
            created_at__lt=end_date
        ).values('product__id', 'product__name').annotate(
            total_pieces=Sum('quantity_pieces'),
            total_bf=Sum('board_feet')
        )
        
        usage = StockTransaction.objects.filter(
            transaction_type='stock_out',
            created_at__gte=start_date,
            created_at__lt=end_date
        ).values('product__id', 'product__name').annotate(
            total_pieces=Sum('quantity_pieces'),
            total_bf=Sum('board_feet')
        )
        
        return {
            'period': f'{year}-{month:02d}',
            'purchases': list(purchases),
            'usage': list(usage)
        }
    
    @staticmethod
    def wastage_report(start_date=None, end_date=None):
        """
        Get wastage report (adjustments with negative quantities)
        
        Args:
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)
            
        Returns:
            Dict with wastage data
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        wastage = StockTransaction.objects.filter(
            transaction_type='adjustment',
            created_at__gte=start_date,
            created_at__lte=end_date,
            reason__icontains='damaged'
        ).values('product__id', 'product__name', 'reason').annotate(
            total_pieces=Sum('quantity_pieces'),
            total_bf=Sum('board_feet'),
            count=Count('id')
        ).order_by('-total_bf')
        
        total_wastage = sum(float(w['total_bf']) for w in wastage)
        total_pieces_wasted = sum(w['total_pieces'] for w in wastage)
        
        return {
            'period': f'{start_date.date()} to {end_date.date()}',
            'total_pieces_wasted': total_pieces_wasted,
            'total_bf_wasted': total_wastage,
            'items': list(wastage)
        }
    
    @staticmethod
    def inventory_turnover(days=30):
        """
        Calculate inventory turnover rate
        
        Args:
            days: Period in days
            
        Returns:
            Dict with turnover metrics
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        products = LumberProduct.objects.filter(is_active=True).annotate(
            stock_outs=Count(
                'stock_transactions',
                filter=Q(stock_transactions__transaction_type='stock_out',
                        stock_transactions__created_at__gte=cutoff_date)
            ),
            avg_inventory=Avg(
                'inventory_snapshots__total_board_feet',
                filter=Q(inventory_snapshots__snapshot_date__gte=cutoff_date.date())
            )
        ).filter(stock_outs__gt=0).values(
            'id', 'name', 'stock_outs', 'avg_inventory'
        ).order_by('-stock_outs')
        
        return {
            'period_days': days,
            'data': list(products)
        }
    
    @staticmethod
    def stock_value_report():
        """
        Calculate total inventory value by category and product
        
        Returns:
            Dict with inventory value breakdown
        """
        categories = {}
        total_value = Decimal('0')
        
        for inventory in Inventory.objects.select_related('product', 'product__category'):
            category_name = inventory.product.category.get_name_display()
            value = inventory.total_board_feet * inventory.product.price_per_board_foot
            total_value += value
            
            if category_name not in categories:
                categories[category_name] = {
                    'value': Decimal('0'),
                    'products': []
                }
            
            categories[category_name]['value'] += value
            categories[category_name]['products'].append({
                'product_id': inventory.product.id,
                'product_name': inventory.product.name,
                'bf': float(inventory.total_board_feet),
                'price_per_bf': float(inventory.product.price_per_board_foot),
                'value': float(value)
            })
        
        return {
            'total_inventory_value': float(total_value),
            'by_category': {k: {
                'value': float(v['value']),
                'products': v['products']
            } for k, v in categories.items()}
        }
