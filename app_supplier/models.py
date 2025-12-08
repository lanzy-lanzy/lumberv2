from django.db import models
from django.core.validators import MinValueValidator
from app_inventory.models import LumberProduct


class Supplier(models.Model):
    """Supplier information"""
    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    
    delivery_speed_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=5.0,
        validators=[MinValueValidator(0), ],
        help_text="Rating out of 5"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.company_name


class PurchaseOrder(models.Model):
    """Purchase order to supplier"""
    PO_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('confirmed', 'Confirmed'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    
    status = models.CharField(max_length=20, choices=PO_STATUS_CHOICES, default='draft')
    
    expected_delivery_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('core.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    received_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['po_number']), models.Index(fields=['status', '-created_at'])]
    
    def __str__(self):
        return f"{self.po_number} - {self.supplier.company_name}"
    
    def calculate_total(self):
        """Calculate total from line items"""
        total = sum(item.subtotal for item in self.po_items.all())
        return total


class PurchaseOrderItem(models.Model):
    """Line items in a purchase order"""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='po_items')
    product = models.ForeignKey(LumberProduct, on_delete=models.PROTECT)
    
    quantity_pieces = models.IntegerField(validators=[MinValueValidator(1)])
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Purchase Order Items'
    
    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.product.name}"


class SupplierPriceHistory(models.Model):
    """Track pricing history per supplier"""
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='price_history')
    product = models.ForeignKey(LumberProduct, on_delete=models.CASCADE, related_name='supplier_prices')
    
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Supplier Price Histories'
        ordering = ['-valid_from']
    
    def __str__(self):
        return f"{self.supplier.company_name} - {self.product.name}"
