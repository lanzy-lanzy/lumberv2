from django.contrib import admin
from app_delivery.models import Delivery, DeliveryLog


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('delivery_number', 'sales_order', 'status', 'driver_name', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('delivery_number', 'driver_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(DeliveryLog)
class DeliveryLogAdmin(admin.ModelAdmin):
    list_display = ('delivery', 'status', 'updated_by', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at',)
