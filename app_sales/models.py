from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from app_inventory.models import LumberProduct
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


class Customer(models.Model):
    """Customer information"""
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    
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
    
    ORDER_SOURCE_CHOICES = [
        ('customer_order', 'Customer Order'),
        ('point_of_sale', 'Point of Sale / Walk-in'),
    ]
    
    SO_NUMBER_PATTERN = 'SO-'  # Will be auto-generated
    
    so_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales_orders')
    order_source = models.CharField(max_length=20, choices=ORDER_SOURCE_CHOICES, default='point_of_sale')
    
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # percentage
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    
    # Order confirmation fields
    is_confirmed = models.BooleanField(default=False, help_text='Order confirmed by admin - prevents further edits')
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text='When the order was confirmed')
    confirmed_by = models.ForeignKey('core.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_orders', help_text='Admin who confirmed this order')
    
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
        """Recalculate discount and balance"""
        # Calculate discount amount from discount percentage
        self.discount_amount = (self.total_amount * self.discount) / 100
        # Recalculate balance
        self.balance = self.total_amount - self.discount_amount - self.amount_paid


class SalesOrderItem(models.Model):
    """Line items in a sales order"""
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='sales_order_items')
    product = models.ForeignKey(LumberProduct, on_delete=models.CASCADE)
    
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
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='receipts')
    
    amount_tendered = models.DecimalField(max_digits=12, decimal_places=2)
    change = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_by = models.ForeignKey('core.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.receipt_number} - {self.sales_order.so_number}"


class ShoppingCart(models.Model):
    """Shopping cart for customers"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shopping_cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_total(self):
        """Get total price of all items in cart"""
        return sum(item.get_subtotal() for item in self.items.all())
    
    def get_total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())
    
    def get_item_count(self):
        """Get count of unique items in cart"""
        return self.items.count()
    
    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()
    
    def __str__(self):
        return f"Cart for {self.user.get_full_name()}"
    
    class Meta:
        verbose_name = 'Shopping Cart'
        verbose_name_plural = 'Shopping Carts'


class CartItem(models.Model):
    """Individual item in a shopping cart"""
    cart = models.ForeignKey(ShoppingCart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(LumberProduct, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_price(self):
        """Get unit price of product"""
        return self.product.price_per_piece or (self.product.price_per_board_foot * self.product.board_feet)
    
    def get_subtotal(self):
        """Get subtotal for this item"""
        return Decimal(str(self.quantity)) * self.get_price()
    
    def is_in_stock(self):
        """Check if product has enough inventory"""
        inventory = getattr(self.product, 'inventory', None)
        if not inventory:
            return False
        return inventory.quantity_pieces >= self.quantity
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ('cart', 'product')


# Signal to create cart when user is created
@receiver(post_save, sender=User)
def create_shopping_cart(sender, instance, created, **kwargs):
    """Automatically create a shopping cart for new users"""
    if created and instance.is_customer():
        ShoppingCart.objects.get_or_create(user=instance)
