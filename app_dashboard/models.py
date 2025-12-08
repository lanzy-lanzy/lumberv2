from django.db import models
from app_inventory.models import LumberProduct


class DashboardMetric(models.Model):
    """Dashboard metrics for reporting"""
    METRIC_TYPE_CHOICES = [
        ('total_stock', 'Total Stock'),
        ('low_stock_alert', 'Low Stock Alert'),
        ('fast_moving', 'Fast Moving Items'),
        ('overstock', 'Overstock'),
        ('price_change', 'Price Change'),
        ('daily_sales', 'Daily Sales'),
        ('monthly_sales', 'Monthly Sales'),
    ]
    
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPE_CHOICES)
    product = models.ForeignKey(LumberProduct, on_delete=models.CASCADE, null=True, blank=True)
    
    value = models.DecimalField(max_digits=15, decimal_places=2)
    threshold = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_at']
        verbose_name_plural = 'Dashboard Metrics'
        indexes = [models.Index(fields=['metric_type', '-recorded_at'])]
    
    def __str__(self):
        return f"{self.get_metric_type_display()} - {self.value}"
