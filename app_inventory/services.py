"""
Inventory management services for Stock In, Stock Out, and Adjustments
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from app_inventory.models import Inventory, StockTransaction, LumberProduct
from app_supplier.models import SupplierPriceHistory


class InventoryService:
    """Service for managing inventory operations"""
    
    @staticmethod
    @transaction.atomic
    def stock_in(product_id, quantity_pieces, supplier_id=None, cost_per_unit=None, created_by=None, reference_id=None):
        """
        Add stock to inventory (receiving)
        
        Args:
            product_id: LumberProduct ID
            quantity_pieces: Number of pieces received
            supplier_id: Supplier ID (optional)
            cost_per_unit: Cost per piece
            created_by: User performing the action
            reference_id: PO number or reference
            
        Returns:
            StockTransaction: The created transaction
        """
        product = LumberProduct.objects.get(id=product_id)
        board_feet = product.calculate_board_feet(quantity_pieces)
        
        # Update or create inventory
        inventory, created = Inventory.objects.get_or_create(product=product)
        inventory.quantity_pieces += quantity_pieces
        inventory.total_board_feet += Decimal(str(board_feet))
        inventory.save()
        
        # Create transaction record
        transaction_obj = StockTransaction.objects.create(
            product=product,
            transaction_type='stock_in',
            quantity_pieces=quantity_pieces,
            board_feet=Decimal(str(board_feet)),
            cost_per_unit=cost_per_unit,
            reference_id=reference_id,
            created_by=created_by
        )
        
        # Update supplier price history if provided
        if supplier_id and cost_per_unit:
            SupplierPriceHistory.objects.filter(
                supplier_id=supplier_id,
                product=product,
                valid_to__isnull=True
            ).update(valid_to=timezone.now().date())
            
            SupplierPriceHistory.objects.create(
                supplier_id=supplier_id,
                product=product,
                price_per_unit=cost_per_unit,
                valid_from=timezone.now().date()
            )
        
        return transaction_obj
    
    @staticmethod
    @transaction.atomic
    def stock_out(product_id, quantity_pieces, reason='sales', created_by=None, reference_id=None):
        """
        Remove stock from inventory
        
        Args:
            product_id: LumberProduct ID
            quantity_pieces: Number of pieces to remove
            reason: Reason for stock out (sales, delivery, wastage, etc.)
            created_by: User performing the action
            reference_id: SO number, delivery ID, etc.
            
        Returns:
            StockTransaction or None: The created transaction, or None if insufficient stock
        """
        product = LumberProduct.objects.get(id=product_id)
        inventory = Inventory.objects.get(product=product)
        
        # Check if sufficient stock available
        if inventory.quantity_pieces < quantity_pieces:
            raise ValueError(f"Insufficient stock. Available: {inventory.quantity_pieces}, Requested: {quantity_pieces}")
        
        board_feet = product.calculate_board_feet(quantity_pieces)
        
        # Update inventory
        inventory.quantity_pieces -= quantity_pieces
        inventory.total_board_feet -= Decimal(str(board_feet))
        
        # Safeguard: prevent negative BF if pieces are 0
        if inventory.quantity_pieces <= 0:
            inventory.quantity_pieces = 0
            inventory.total_board_feet = Decimal('0')
        elif inventory.total_board_feet < 0:
            # If pieces > 0 but BF < 0, recalculate to fix drift
            inventory.total_board_feet = Decimal(str(product.calculate_board_feet(inventory.quantity_pieces)))
            
        inventory.save()
        
        # Create transaction record
        transaction_obj = StockTransaction.objects.create(
            product=product,
            transaction_type='stock_out',
            quantity_pieces=quantity_pieces,
            board_feet=Decimal(str(board_feet)),
            reason=reason,
            reference_id=reference_id,
            created_by=created_by
        )
        
        return transaction_obj
    
    @staticmethod
    @transaction.atomic
    def adjust_stock(product_id, quantity_change, reason, created_by=None):
        """
        Adjust stock with reason (damaged, miscount, recut, lost, etc.)
        
        Args:
            product_id: LumberProduct ID
            quantity_change: Positive or negative quantity change
            reason: Reason for adjustment
            created_by: User performing the action
            
        Returns:
            StockTransaction: The created transaction
        """
        product = LumberProduct.objects.get(id=product_id)
        inventory = Inventory.objects.get(product=product)
        
        # Check if adjustment would result in negative inventory
        new_quantity = inventory.quantity_pieces + quantity_change
        if new_quantity < 0:
            raise ValueError(f"Adjustment would result in negative inventory: {new_quantity}")
        
        board_feet_change = product.calculate_board_feet(abs(quantity_change))
        if quantity_change < 0:
            board_feet_change = -board_feet_change
        
        # Update inventory
        inventory.quantity_pieces = new_quantity
        inventory.total_board_feet += Decimal(str(board_feet_change))
        
        # Safeguard: prevent negative BF if pieces are 0
        if inventory.quantity_pieces <= 0:
            inventory.quantity_pieces = 0
            inventory.total_board_feet = Decimal('0')
        elif inventory.total_board_feet < 0:
            # If pieces > 0 but BF < 0, recalculate to fix drift
            inventory.total_board_feet = Decimal(str(product.calculate_board_feet(inventory.quantity_pieces)))
            
        inventory.save()
        
        # Create transaction record (use positive number and track direction in reason)
        transaction_obj = StockTransaction.objects.create(
            product=product,
            transaction_type='adjustment',
            quantity_pieces=abs(quantity_change),
            board_feet=Decimal(str(abs(board_feet_change))),
            reason=f"{reason} ({'+' if quantity_change > 0 else '-'})",
            created_by=created_by
        )
        
        return transaction_obj
    
    @staticmethod
    def get_low_stock_products(threshold_bf=100):
        """
        Get products below stock threshold
        
        Args:
            threshold_bf: Board feet threshold
            
        Returns:
            QuerySet: Inventory records below threshold
        """
        return Inventory.objects.filter(total_board_feet__lt=threshold_bf).select_related('product')
    
    @staticmethod
    def get_fast_moving_items(days=30, min_transactions=5):
        """
        Get fast-moving items (high volume sales)
        
        Args:
            days: Number of days to look back
            min_transactions: Minimum number of transactions
            
        Returns:
            Dict: Product info and transaction count
        """
        from django.db.models import Count, Q
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        products = LumberProduct.objects.filter(
            stock_transactions__transaction_type='stock_out',
            stock_transactions__created_at__gte=cutoff_date
        ).annotate(
            transaction_count=Count('stock_transactions', filter=Q(stock_transactions__transaction_type='stock_out'))
        ).filter(
            transaction_count__gte=min_transactions
        ).order_by('-transaction_count').values('id', 'name', 'transaction_count')
        
        return products
    
    @staticmethod
    def get_overstock_products(max_bf=5000):
        """
        Get overstocked items
        
        Args:
            max_bf: Board feet threshold for overstock
            
        Returns:
            QuerySet: Inventory records above threshold
        """
        return Inventory.objects.filter(total_board_feet__gt=max_bf).select_related('product')

    @staticmethod
    @transaction.atomic
    def recalculate_inventory_stats(product_id=None):
        """
        Recalculate total_board_feet for inventory items to fix data drift.
        If product_id is None, recalculates all products.
        """
        if product_id:
            inventories = Inventory.objects.filter(product_id=product_id)
        else:
            inventories = Inventory.objects.all()
            
        results = []
        for inv in inventories:
            old_bf = inv.total_board_feet
            product = inv.product
            # Board Feet = (Thickness x Width x Length) / 12
            new_bf = Decimal(str(product.calculate_board_feet(inv.quantity_pieces)))
            
            if old_bf != new_bf:
                inv.total_board_feet = new_bf
                inv.save()
                results.append({
                    'product': product.name,
                    'old_bf': float(old_bf),
                    'new_bf': float(new_bf)
                })
        return results
