from django.contrib import admin
from app_sales.models import Customer, SalesOrder, SalesOrderItem, Receipt


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'email', 'is_senior', 'is_pwd', 'created_at')
    list_filter = ('is_senior', 'is_pwd')
    search_fields = ('name', 'phone_number', 'email')


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ('so_number', 'customer', 'total_amount', 'payment_type', 'balance', 'created_at')
    list_filter = ('payment_type', 'created_at')
    search_fields = ('so_number', 'customer__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SalesOrderItem)
class SalesOrderItemAdmin(admin.ModelAdmin):
    list_display = ('sales_order', 'product', 'quantity_pieces', 'unit_price', 'subtotal')


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'sales_order', 'amount_tendered', 'change', 'created_at')
    readonly_fields = ('created_at',)
