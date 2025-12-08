"""
Unified reporting and analytics dashboard
"""
from decimal import Decimal
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta, date
from app_inventory.models import Inventory, StockTransaction, LumberProduct
from app_sales.models import SalesOrder, SalesOrderItem, Customer
from app_delivery.models import Delivery
from app_supplier.models import PurchaseOrder, Supplier, SupplierPriceHistory


class ComprehensiveReports:
    """Comprehensive reporting system"""
    
    @staticmethod
    def executive_summary(days=30):
        """
        Get executive dashboard summary
        
        Args:
            days: Period in days
            
        Returns:
            Dict with key metrics
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Sales metrics
        total_sales = SalesOrder.objects.filter(
            created_at__gte=cutoff_date
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        
        sales_count = SalesOrder.objects.filter(
            created_at__gte=cutoff_date
        ).count()
        
        # Inventory metrics
        inventory_value = Decimal('0')
        for inv in Inventory.objects.all():
            inventory_value += inv.total_board_feet * inv.product.price_per_board_foot
        
        # Delivery metrics
        deliveries_completed = Delivery.objects.filter(
            status='delivered',
            delivered_at__gte=cutoff_date
        ).count()
        
        deliveries_pending = Delivery.objects.filter(
            status__in=['pending', 'on_picking', 'loaded', 'out_for_delivery'],
            created_at__gte=cutoff_date
        ).count()
        
        # Purchase metrics
        total_purchases = PurchaseOrder.objects.filter(
            created_at__gte=cutoff_date,
            status='received'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        
        purchase_count = PurchaseOrder.objects.filter(
            created_at__gte=cutoff_date,
            status='received'
        ).count()
        
        # Customers
        unique_customers = Customer.objects.filter(
            sales_orders__created_at__gte=cutoff_date
        ).distinct().count()
        
        # Credit/Outstanding metrics
        outstanding = SalesOrder.objects.filter(
            payment_type='credit',
            balance__gt=0
        ).aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
        
        customers_with_credit = SalesOrder.objects.filter(
            payment_type='credit',
            balance__gt=0
        ).values('customer').distinct().count()
        
        return {
            'period_days': days,
            'sales': {
                'total': float(total_sales),
                'transactions': sales_count,
                'avg_transaction': float(total_sales / sales_count) if sales_count > 0 else 0
            },
            'inventory': {
                'total_value': float(inventory_value),
                'products_active': LumberProduct.objects.filter(is_active=True).count(),
                'low_stock_alerts': Inventory.objects.filter(total_board_feet__lt=100).count()
            },
            'deliveries': {
                'completed': deliveries_completed,
                'pending': deliveries_pending,
                'total': deliveries_completed + deliveries_pending
            },
            'purchasing': {
                'total_spent': float(total_purchases),
                'orders': purchase_count,
                'suppliers': Supplier.objects.filter(
                    purchase_orders__created_at__gte=cutoff_date
                ).distinct().count()
            },
            'customers': {
                'unique': unique_customers,
                'total': Customer.objects.count()
            },
            'credit': {
                'outstanding': float(outstanding),
                'customer_count': customers_with_credit
            }
        }
    
    @staticmethod
    def low_stock_alert():
        """
        Get all products with low stock
        
        Returns:
            List of low stock products
        """
        low_stock = Inventory.objects.filter(
            total_board_feet__lt=100
        ).select_related('product').order_by('total_board_feet')
        
        return [{
            'product_id': inv.product.id,
            'product_name': inv.product.name,
            'sku': inv.product.sku,
            'quantity_pieces': inv.quantity_pieces,
            'board_feet': float(inv.total_board_feet),
            'price_per_bf': float(inv.product.price_per_board_foot),
            'estimated_value': float(inv.total_board_feet * inv.product.price_per_board_foot)
        } for inv in low_stock]
    
    @staticmethod
    def overstock_alert(threshold_bf=5000):
        """
        Get overstocked products
        
        Args:
            threshold_bf: Overstock threshold in board feet
            
        Returns:
            List of overstocked products
        """
        overstock = Inventory.objects.filter(
            total_board_feet__gt=threshold_bf
        ).select_related('product').order_by('-total_board_feet')
        
        return [{
            'product_id': inv.product.id,
            'product_name': inv.product.name,
            'sku': inv.product.sku,
            'quantity_pieces': inv.quantity_pieces,
            'board_feet': float(inv.total_board_feet),
            'price_per_bf': float(inv.product.price_per_board_foot),
            'estimated_value': float(inv.total_board_feet * inv.product.price_per_board_foot)
        } for inv in overstock]
    
    @staticmethod
    def aged_receivables(days_threshold=30):
        """
        Get aged receivables (credit/SOA orders)
        
        Args:
            days_threshold: Days past due
            
        Returns:
            List of aged receivables
        """
        cutoff_date = timezone.now() - timedelta(days=days_threshold)
        
        aged = SalesOrder.objects.filter(
            payment_type='credit',
            balance__gt=0,
            created_at__lte=cutoff_date
        ).select_related('customer').order_by('-created_at')
        
        total = Decimal('0')
        items = []
        for so in aged:
            total += so.balance
            items.append({
                'so_number': so.so_number,
                'customer_name': so.customer.name,
                'customer_id': so.customer.id,
                'total_amount': float(so.total_amount),
                'amount_paid': float(so.amount_paid),
                'balance': float(so.balance),
                'days_old': (timezone.now() - so.created_at).days,
                'created_at': so.created_at.isoformat()
            })
        
        return {
            'days_threshold': days_threshold,
            'total_outstanding': float(total),
            'count': len(items),
            'items': items
        }
    
    @staticmethod
    def product_performance(days=30):
        """
        Get product performance metrics
        
        Args:
            days: Period in days
            
        Returns:
            List of products with sales metrics
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        products = SalesOrderItem.objects.filter(
            sales_order__created_at__gte=cutoff_date
        ).values('product__id', 'product__name', 'product__sku').annotate(
            total_pieces=Sum('quantity_pieces'),
            total_bf=Sum('board_feet'),
            total_revenue=Sum('subtotal'),
            transaction_count=Count('sales_order'),
            avg_unit_price=Avg('unit_price')
        ).order_by('-total_revenue')
        
        return list(products)
    
    @staticmethod
    def category_performance(days=30):
        """
        Get category performance
        
        Args:
            days: Period in days
            
        Returns:
            Dict with category metrics
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        categories = SalesOrderItem.objects.filter(
            sales_order__created_at__gte=cutoff_date
        ).values('product__category__name').annotate(
            total_revenue=Sum('subtotal'),
            total_items=Count('id'),
            total_pieces=Sum('quantity_pieces'),
            avg_item_value=Avg('subtotal'),
            margin_estimate=Sum('subtotal')  # Would need cost tracking for actual margin
        ).order_by('-total_revenue')
        
        return list(categories)
    
    @staticmethod
    def cash_flow_summary(days=30):
        """
        Get cash flow summary
        
        Args:
            days: Period in days
            
        Returns:
            Dict with cash flow data
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Cash inflows from sales
        cash_sales = SalesOrder.objects.filter(
            created_at__gte=cutoff_date,
            payment_type__in=['cash', 'partial']
        ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0')
        
        # Credit sales (to be collected)
        credit_sales = SalesOrder.objects.filter(
            created_at__gte=cutoff_date,
            payment_type='credit'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        
        # Cash outflows (purchases)
        cash_outflows = PurchaseOrder.objects.filter(
            created_at__gte=cutoff_date,
            status='received'
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        
        # Net cash position estimate
        net_position = cash_sales - cash_outflows
        
        return {
            'period_days': days,
            'cash_inflows': float(cash_sales),
            'credit_sales_outstanding': float(credit_sales),
            'cash_outflows': float(cash_outflows),
            'net_cash_position': float(net_position),
            'outstanding_receivables': float(
                SalesOrder.objects.filter(
                    payment_type='credit',
                    balance__gt=0
                ).aggregate(Sum('balance'))['balance__sum'] or 0
            )
        }
    
    @staticmethod
    def supplier_analysis(days=30):
        """
        Get supplier performance analysis
        
        Args:
            days: Period in days
            
        Returns:
            List of supplier metrics
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        suppliers = Supplier.objects.filter(
            purchase_orders__created_at__gte=cutoff_date
        ).annotate(
            total_spent=Sum('purchase_orders__total_amount'),
            po_count=Count('purchase_orders'),
            received_count=Count('purchase_orders', filter=Q(purchase_orders__status='received')),
            pending_count=Count('purchase_orders', filter=Q(purchase_orders__status='confirmed'))
        ).distinct().order_by('-total_spent')
        
        return [{
            'supplier_id': s.id,
            'company_name': s.company_name,
            'contact_person': s.contact_person,
            'total_spent': float(s.total_spent or 0),
            'po_count': s.po_count,
            'received_count': s.received_count,
            'pending_count': s.pending_count,
            'fulfillment_rate': round((s.received_count / s.po_count * 100), 1) if s.po_count > 0 else 0,
            'delivery_rating': float(s.delivery_speed_rating)
        } for s in suppliers]
    
    @staticmethod
    def inventory_composition():
        """
        Get inventory composition by category
        
        Returns:
            Dict with inventory breakdown
        """
        categories = {}
        total_value = Decimal('0')
        total_bf = Decimal('0')
        
        for inv in Inventory.objects.select_related('product', 'product__category'):
            category_name = inv.product.category.get_name_display()
            value = inv.total_board_feet * inv.product.price_per_board_foot
            total_value += value
            total_bf += inv.total_board_feet
            
            if category_name not in categories:
                categories[category_name] = {
                    'value': Decimal('0'),
                    'board_feet': Decimal('0'),
                    'product_count': 0,
                    'products': []
                }
            
            categories[category_name]['value'] += value
            categories[category_name]['board_feet'] += inv.total_board_feet
            categories[category_name]['product_count'] += 1
            categories[category_name]['products'].append({
                'product_id': inv.product.id,
                'product_name': inv.product.name,
                'sku': inv.product.sku,
                'pieces': inv.quantity_pieces,
                'board_feet': float(inv.total_board_feet),
                'value': float(value)
            })
        
        return {
            'total_inventory_value': float(total_value),
            'total_board_feet': float(total_bf),
            'categories': {k: {
                'value': float(v['value']),
                'board_feet': float(v['board_feet']),
                'product_count': v['product_count'],
                'percentage_of_total': round((float(v['value']) / float(total_value) * 100), 1) if total_value > 0 else 0,
                'products': v['products']
            } for k, v in categories.items()}
        }
