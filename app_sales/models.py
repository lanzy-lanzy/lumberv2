from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from app_inventory.models import LumberProduct


class Customer(models.Model):
    """Customer information"""
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    
    is_senior = models.BooleanField(default=False)
    is_pwd = models.BooleanField(default=False, verbose_name='PWD (Person with Disability)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class SalesOrder(models.Model):
    """Sales order record"""
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('partial', 'Partial Payment'),
        ('credit', 'Credit (SOA)'),
    ]
    
    SO_NUMBER_PATTERN = 'SO-'  # Will be auto-generated
    
    so_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales_orders')
    
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # percentage
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('core.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['so_number']), models.Index(fields=['-created_at'])]
    
    def __str__(self):
        return f"{self.so_number} - {self.customer.name}"
    
    def calculate_total(self):
        """Calculate total from line items"""
        total = sum(item.subtotal for item in self.sales_order_items.all())
        return total
    
    def apply_discount(self):
        """Apply discount based on eligibility"""
        if self.customer.is_senior or self.customer.is_pwd:
            self.discount = Decimal('20.00')  # 20% discount
        
        self.discount_amount = (self.total_amount * self.discount) / 100
        self.balance = self.total_amount - self.discount_amount - self.amount_paid


class SalesOrderItem(models.Model):
    """Line items in a sales order"""
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='sales_order_items')
    product = models.ForeignKey(LumberProduct, on_delete=models.PROTECT)
    
    quantity_pieces = models.IntegerField(validators=[MinValueValidator(1)])
    board_feet = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Sales Order Items'
    
    def __str__(self):
        return f"{self.sales_order.so_number} - {self.product.name}"
    
    def calculate_board_feet(self):
        """Calculate board feet for this line item"""
        return self.product.calculate_board_feet(self.quantity_pieces)


class Receipt(models.Model):
    """Receipt for sales order"""
    receipt_number = models.CharField(max_length=50, unique=True)
    sales_order = models.OneToOneField(SalesOrder, on_delete=models.CASCADE, related_name='receipt')
    
    amount_tendered = models.DecimalField(max_digits=12, decimal_places=2)
    change = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_by = models.ForeignKey('core.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.receipt_number} - {self.sales_order.so_number}"
