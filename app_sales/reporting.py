"""
Sales reporting and analytics
"""
from decimal import Decimal
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta, date
from app_sales.models import SalesOrder, SalesOrderItem, Customer, Receipt


class SalesReports:
    """Generate sales reports"""
    
    @staticmethod
    def daily_sales_summary(sales_date=None):
        """
        Get daily sales summary
        
        Args:
            sales_date: Date to report on (default: today)
            
        Returns:
            Dict with daily sales data
        """
        if not sales_date:
            sales_date = timezone.now().date()
        
        orders = SalesOrder.objects.filter(created_at__date=sales_date)
        
        total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        total_discount = orders.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0')
        total_paid = orders.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0')
        outstanding = orders.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
        
        payment_breakdown = orders.values('payment_type').annotate(
            count=Count('id'),
            total=Sum('total_amount'),
            paid=Sum('amount_paid')
        )
        
        return {
            'date': sales_date,
            'total_sales': float(total_sales),
            'total_discount': float(total_discount),
            'net_sales': float(total_sales - total_discount),
            'total_paid': float(total_paid),
            'outstanding_balance': float(outstanding),
            'transactions': orders.count(),
            'by_payment_type': list(payment_breakdown)
        }
    
    @staticmethod
    def top_customers(days=30, limit=10):
        """
        Get top customers by sales
        
        Args:
            days: Period in days
            limit: Number of top customers to return
            
        Returns:
            List of top customers with sales data
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        customers = Customer.objects.filter(
            sales_orders__created_at__gte=cutoff_date
        ).annotate(
            total_spent=Sum('sales_orders__total_amount'),
            transaction_count=Count('sales_orders')
        ).order_by('-total_spent')[:limit]
        
        return [{
            'customer_id': c.id,
            'customer_name': c.name,
            'phone': c.phone_number,
            'total_spent': float(c.total_spent),
            'transaction_count': c.transaction_count,
            'avg_transaction': float(c.total_spent / c.transaction_count) if c.transaction_count > 0 else 0
        } for c in customers]
    
    @staticmethod
    def top_items(days=30, limit=10):
        """
        Get top selling items
        
        Args:
            days: Period in days
            limit: Number of top items to return
            
        Returns:
            List of top items with sales data
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        items = SalesOrderItem.objects.filter(
            sales_order__created_at__gte=cutoff_date
        ).values('product__id', 'product__name', 'product__sku').annotate(
            total_pieces=Sum('quantity_pieces'),
            total_bf=Sum('board_feet'),
            total_revenue=Sum('subtotal'),
            transaction_count=Count('sales_order')
        ).order_by('-total_revenue')[:limit]
        
        return list(items)
    
    @staticmethod
    def income_by_category(days=30):
        """
        Get income breakdown by product category
        
        Args:
            days: Period in days
            
        Returns:
            Dict with income by category
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        categories = SalesOrderItem.objects.filter(
            sales_order__created_at__gte=cutoff_date
        ).values('product__category__name').annotate(
            total_revenue=Sum('subtotal'),
            total_items=Count('id'),
            total_pieces=Sum('quantity_pieces'),
            avg_item_value=Avg('subtotal')
        ).order_by('-total_revenue')
        
        return list(categories)
    
    @staticmethod
    def senior_pwd_discount_summary(days=30):
        """
        Get summary of senior/PWD discounts
        
        Args:
            days: Period in days
            
        Returns:
            Dict with discount data
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        senior_orders = SalesOrder.objects.filter(
            created_at__gte=cutoff_date,
            customer__is_senior=True
        )
        
        pwd_orders = SalesOrder.objects.filter(
            created_at__gte=cutoff_date,
            customer__is_pwd=True
        )
        
        senior_discount = senior_orders.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0')
        pwd_discount = pwd_orders.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0')
        total_discount = senior_orders.union(pwd_orders).aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0')
        
        return {
            'period_days': days,
            'senior_customers': senior_orders.count(),
            'senior_discount': float(senior_discount),
            'pwd_customers': pwd_orders.count(),
            'pwd_discount': float(pwd_discount),
            'total_discounted_orders': senior_orders.union(pwd_orders).count(),
            'total_discount_given': float(total_discount)
        }
    
    @staticmethod
    def credit_sales_outstanding(days=None):
        """
        Get outstanding credit/SOA balance
        
        Args:
            days: Only show orders created within last N days (optional)
            
        Returns:
            List of credit orders with outstanding balances
        """
        query = SalesOrder.objects.filter(payment_type='credit', balance__gt=0).select_related('customer')
        
        if days:
            cutoff_date = timezone.now() - timedelta(days=days)
            query = query.filter(created_at__gte=cutoff_date)
        
        total_outstanding = query.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
        
        return {
            'total_outstanding': float(total_outstanding),
            'orders_count': query.count(),
            'orders': [{
                'so_number': so.so_number,
                'customer_id': so.customer.id,
                'customer_name': so.customer.name,
                'total_amount': float(so.total_amount),
                'amount_paid': float(so.amount_paid),
                'balance': float(so.balance),
                'created_at': so.created_at
            } for so in query.order_by('-balance')]
        }
    
    @staticmethod
    def sales_trend(days=30):
        """
        Get sales trend over period
        
        Args:
            days: Period in days
            
        Returns:
            List of daily sales data
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        sales = SalesOrder.objects.filter(
            created_at__gte=cutoff_date
        ).extra(
            select={'date': 'DATE(created_at)'}
        ).values('date').annotate(
            total=Sum('total_amount'),
            count=Count('id'),
            avg=Avg('total_amount')
        ).order_by('date')
        
        return list(sales)
