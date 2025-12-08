from django.db import models
from app_sales.models import SalesOrder


class Delivery(models.Model):
    """Delivery tracking"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('on_picking', 'On Picking'),
        ('loaded', 'Loaded'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
    ]
    
    delivery_number = models.CharField(max_length=50, unique=True)
    sales_order = models.OneToOneField(SalesOrder, on_delete=models.PROTECT, related_name='delivery')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    driver_name = models.CharField(max_length=200, blank=True)
    plate_number = models.CharField(max_length=20, blank=True)
    customer_signature = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['delivery_number']), models.Index(fields=['status', '-created_at'])]
    
    def __str__(self):
        return f"{self.delivery_number} - {self.get_status_display()}"


class DeliveryLog(models.Model):
    """Detailed delivery log"""
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='delivery_logs')
    
    status = models.CharField(max_length=20, choices=Delivery.STATUS_CHOICES)
    notes = models.TextField(blank=True)
    
    updated_by = models.ForeignKey('core.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Delivery Logs'
    
    def __str__(self):
        return f"{self.delivery.delivery_number} - {self.get_status_display()}"
