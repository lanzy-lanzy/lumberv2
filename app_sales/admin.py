from django.contrib import admin
from app_sales.models import Customer, SalesOrder, SalesOrderItem, Receipt, ShoppingCart, CartItem
from app_sales.notification_models import OrderNotification, OrderConfirmation


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'email', 'created_at')
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


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_item_count', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_item_count(self, obj):
        return obj.get_item_count()
    get_item_count.short_description = 'Items'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'get_price', 'get_subtotal', 'added_at')
    search_fields = ('cart__user__username', 'product__name', 'product__sku')
    readonly_fields = ('added_at', 'updated_at')
    
    def get_price(self, obj):
        return f"₱{obj.get_price():.2f}"
    get_price.short_description = 'Unit Price'
    
    def get_subtotal(self, obj):
        return f"₱{obj.get_subtotal():.2f}"
    get_subtotal.short_description = 'Subtotal'


@admin.register(OrderConfirmation)
class OrderConfirmationAdmin(admin.ModelAdmin):
    list_display = ('get_so_number', 'customer', 'status', 'is_payment_complete', 'estimated_pickup_date', 'ready_at', 'picked_up_at')
    list_filter = ('status', 'is_payment_complete', 'created_at')
    search_fields = ('sales_order__so_number', 'customer__name', 'customer__email')
    readonly_fields = ('created_at', 'updated_at', 'confirmed_at', 'ready_at', 'picked_up_at', 'payment_completed_at')
    actions = ['mark_ready_for_pickup', 'mark_payment_received', 'mark_picked_up']
    fieldsets = (
        ('Order Information', {
            'fields': ('sales_order', 'customer', 'status')
        }),
        ('Pickup Details', {
            'fields': ('estimated_pickup_date', 'actual_pickup_date')
        }),
        ('Payment Status', {
            'fields': ('is_payment_complete', 'payment_completed_at')
        }),
        ('Timestamps', {
            'fields': ('confirmed_at', 'ready_at', 'picked_up_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by')
        }),
    )
    
    def get_so_number(self, obj):
        return obj.sales_order.so_number
    get_so_number.short_description = 'Sales Order'
    
    def mark_ready_for_pickup(self, request, queryset):
        """Admin action to mark orders as ready for pickup"""
        from app_sales.services import OrderConfirmationService
        count = 0
        for confirmation in queryset.filter(status__in=['created', 'confirmed']):
            confirmation.mark_ready_for_pickup()
            count += 1
        self.message_user(request, f"{count} order(s) marked as ready for pickup. Customer(s) have been notified.")
    mark_ready_for_pickup.short_description = "Mark selected orders as ready for pickup and notify customers"
    
    def mark_payment_received(self, request, queryset):
        """Admin action to mark payment as received"""
        count = 0
        for confirmation in queryset:
            if not confirmation.is_payment_complete:
                confirmation.mark_payment_complete()
                count += 1
        self.message_user(request, f"{count} order(s) marked as payment received. Customer(s) have been notified.")
    mark_payment_received.short_description = "Mark selected orders as payment received and notify customers"
    
    def mark_picked_up(self, request, queryset):
        """Admin action to mark orders as picked up"""
        from app_sales.services import OrderConfirmationService
        count = 0
        for confirmation in queryset.filter(status='ready_for_pickup'):
            confirmation.mark_picked_up()
            count += 1
        self.message_user(request, f"{count} order(s) marked as picked up.")
    mark_picked_up.short_description = "Mark selected orders as picked up by customer"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sales_order', 'customer')


@admin.register(OrderNotification)
class OrderNotificationAdmin(admin.ModelAdmin):
    list_display = ('get_so_number', 'customer', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('sales_order__so_number', 'customer__name', 'customer__email', 'title')
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    fieldsets = (
        ('Notification Information', {
            'fields': ('sales_order', 'customer', 'notification_type', 'title')
        }),
        ('Content', {
            'fields': ('message',)
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_so_number(self, obj):
        return obj.sales_order.so_number if obj.sales_order else 'N/A'
    get_so_number.short_description = 'Sales Order'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sales_order', 'customer')
