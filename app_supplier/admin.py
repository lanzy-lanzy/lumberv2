from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from app_supplier.models import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierPriceHistory


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person', 'phone_number', 'email_display', 'delivery_rating_display', 'po_count', 'status_badge', 'created_at')
    list_filter = ('is_active', 'created_at', 'delivery_speed_rating')
    search_fields = ('company_name', 'contact_person', 'phone_number', 'email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Supplier Information', {
            'fields': ('company_name', 'contact_person', 'email', 'phone_number')
        }),
        ('Details', {
            'fields': ('address', 'delivery_speed_rating', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def email_display(self, obj):
        return obj.email or '-'
    email_display.short_description = 'Email'
    
    def delivery_rating_display(self, obj):
        stars = '★' * int(obj.delivery_speed_rating) + '☆' * (5 - int(obj.delivery_speed_rating))
        return format_html(
            '<span style="color: #f59e0b; font-weight: bold;">{}</span>',
            f"{obj.delivery_speed_rating} {stars}"
        )
    delivery_rating_display.short_description = 'Delivery Rating'
    
    def po_count(self, obj):
        count = obj.purchase_orders.count()
        return format_html(
            '<span style="background-color: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            count
        )
    po_count.short_description = 'Purchase Orders'
    
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: bold;">Active</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: bold;">Inactive</span>'
            )
    status_badge.short_description = 'Status'


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    fields = ('product', 'quantity_pieces', 'cost_per_unit', 'subtotal')
    readonly_fields = ('subtotal',)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier_name', 'status_badge', 'total_amount', 'expected_delivery_date', 'days_pending', 'created_at')
    list_filter = ('status', 'created_at', 'expected_delivery_date', 'supplier')
    search_fields = ('po_number', 'supplier__company_name')
    readonly_fields = ('created_at', 'updated_at', 'po_number', 'received_at')
    inlines = [PurchaseOrderItemInline]
    fieldsets = (
        ('Purchase Order Details', {
            'fields': ('po_number', 'supplier', 'status', 'total_amount')
        }),
        ('Dates', {
            'fields': ('expected_delivery_date', 'received_at')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def supplier_name(self, obj):
        return obj.supplier.company_name
    supplier_name.short_description = 'Supplier'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#f3f4f6',
            'submitted': '#fef3c7',
            'confirmed': '#dbeafe',
            'received': '#dcfce7',
            'cancelled': '#fee2e2',
        }
        text_colors = {
            'draft': '#6b7280',
            'submitted': '#92400e',
            'confirmed': '#1e40af',
            'received': '#166534',
            'cancelled': '#991b1b',
        }
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#f3f4f6'),
            text_colors.get(obj.status, '#6b7280'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def days_pending(self, obj):
        from datetime import datetime, date
        if obj.status == 'received':
            return 'Received'
        days = (obj.expected_delivery_date - date.today()).days
        if days < 0:
            return format_html('<span style="color: #dc2626; font-weight: bold;">Overdue ({} days)</span>', abs(days))
        elif days <= 3:
            return format_html('<span style="color: #f59e0b; font-weight: bold;">{} days</span>', days)
        else:
            return format_html('<span style="color: #059669;">{} days</span>', days)
    days_pending.short_description = 'Days to Delivery'


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'product_name', 'quantity_pieces', 'cost_per_unit', 'subtotal')
    list_filter = ('created_at', 'purchase_order__supplier')
    search_fields = ('purchase_order__po_number', 'product__name')
    readonly_fields = ('created_at',)
    
    def po_number(self, obj):
        return obj.purchase_order.po_number
    po_number.short_description = 'PO Number'
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = 'Product'


@admin.register(SupplierPriceHistory)
class SupplierPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('supplier_name', 'product_name', 'price_per_unit', 'valid_from', 'valid_to_display', 'is_current')
    list_filter = ('supplier', 'valid_from', 'valid_to')
    search_fields = ('supplier__company_name', 'product__name')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Price Information', {
            'fields': ('supplier', 'product', 'price_per_unit')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def supplier_name(self, obj):
        return obj.supplier.company_name
    supplier_name.short_description = 'Supplier'
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = 'Product'
    
    def valid_to_display(self, obj):
        return obj.valid_to or 'Current'
    valid_to_display.short_description = 'Valid To'
    
    def is_current(self, obj):
        if obj.valid_to is None:
            return format_html('<span style="background-color: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 3px; font-weight: bold;">Active</span>')
        else:
            return format_html('<span style="background-color: #f3f4f6; color: #6b7280; padding: 2px 6px; border-radius: 3px;">Inactive</span>')
    is_current.short_description = 'Status'
