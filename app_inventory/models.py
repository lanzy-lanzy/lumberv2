from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class LumberCategory(models.Model):
    """Categories for lumber products"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Lumber Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class LumberProduct(models.Model):
    """Lumber product with dimensions and pricing"""
    name = models.CharField(max_length=200)
    category = models.ForeignKey(LumberCategory, on_delete=models.CASCADE)
    
    # Dimensions
    thickness = models.DecimalField(max_digits=5, decimal_places=2)  # in inches
    width = models.DecimalField(max_digits=5, decimal_places=2)      # in inches
    length = models.DecimalField(max_digits=5, decimal_places=2)     # in feet
    
    # Pricing
    price_per_board_foot = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_piece = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Image
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    
    sku = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['sku']), models.Index(fields=['category'])]
    
    def __str__(self):
        return f"{self.name} ({self.thickness}\" x {self.width}\" x {self.length}ft)"
    
    def calculate_board_feet(self, quantity=1):
        """Board Feet = (Thickness x Width x Length) / 12"""
        bf = (self.thickness * self.width * self.length) / 12
        return float(bf) * quantity
    
    @property
    def board_feet(self):
        return float((self.thickness * self.width * self.length) / 12)

    def get_unit_price(self):
        """Returns the appropriate unit price (per piece if set, else per board foot)"""
        if self.price_per_piece:
            return self.price_per_piece
        return self.price_per_board_foot

    def calculate_subtotal(self, quantity=1):
        """Calculates subtotal based on price type"""
        if self.price_per_piece:
            return Decimal(str(self.price_per_piece)) * Decimal(str(quantity))
        
        # Calculate by board feet
        bf = Decimal(str(self.calculate_board_feet(quantity)))
        return bf * Decimal(str(self.price_per_board_foot))


class Inventory(models.Model):
    """Real-time inventory tracking"""
    product = models.OneToOneField(LumberProduct, on_delete=models.CASCADE, related_name='inventory')
    quantity_pieces = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    total_board_feet = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Inventories'
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity_pieces} pcs ({self.total_board_feet} BF)"


class StockTransaction(models.Model):
    """Track all stock movements"""
    TRANSACTION_TYPES = [
        ('stock_in', 'Stock In'),
        ('stock_out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
    ]
    
    product = models.ForeignKey(LumberProduct, on_delete=models.CASCADE, related_name='stock_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity_pieces = models.IntegerField()
    board_feet = models.DecimalField(max_digits=12, decimal_places=2)
    
    reason = models.CharField(max_length=100, blank=True)  # For adjustments
    reference_id = models.CharField(max_length=100, blank=True)  # PO, SO, Delivery ID
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_by = models.ForeignKey('core.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['product', '-created_at'])]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.product.name} ({self.quantity_pieces} pcs)"


class InventorySnapshot(models.Model):
    """Daily inventory snapshots for historical analysis"""
    product = models.ForeignKey(LumberProduct, on_delete=models.CASCADE, related_name='inventory_snapshots')
    
    quantity_pieces = models.IntegerField()
    total_board_feet = models.DecimalField(max_digits=12, decimal_places=2)
    
    snapshot_date = models.DateField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-snapshot_date']
        verbose_name_plural = 'Inventory Snapshots'
        unique_together = ('product', 'snapshot_date')
        indexes = [models.Index(fields=['product', '-snapshot_date'])]
    
    def __str__(self):
        return f"{self.product.name} - {self.snapshot_date}"
