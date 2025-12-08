from django.contrib import admin
from app_inventory.models import LumberCategory, LumberProduct, Inventory, StockTransaction, InventorySnapshot


@admin.register(LumberCategory)
class LumberCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')


@admin.register(LumberProduct)
class LumberProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'sku', 'board_feet', 'price_per_board_foot', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'sku')


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity_pieces', 'total_board_feet', 'last_updated')
    readonly_fields = ('last_updated',)


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('product', 'transaction_type', 'quantity_pieces', 'board_feet', 'created_by', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(InventorySnapshot)
class InventorySnapshotAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity_pieces', 'total_board_feet', 'snapshot_date')
    list_filter = ('snapshot_date', 'product')
    readonly_fields = ('snapshot_date',)
