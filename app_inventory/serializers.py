from rest_framework import serializers
from app_inventory.models import LumberCategory, LumberProduct, Inventory, StockTransaction


class LumberCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LumberCategory
        fields = ['id', 'name', 'description', 'created_at']


class InventoryQuickSerializer(serializers.ModelSerializer):
    """Quick inventory serializer for nested in product"""
    class Meta:
        model = Inventory
        fields = ['quantity_pieces', 'total_board_feet']


class LumberProductSerializer(serializers.ModelSerializer):
    board_feet = serializers.SerializerMethodField()
    inventory = serializers.SerializerMethodField()
    
    class Meta:
        model = LumberProduct
        fields = ['id', 'name', 'category', 'thickness', 'width', 'length', 'board_feet', 
                  'price_per_board_foot', 'price_per_piece', 'sku', 'is_active', 'inventory', 'created_at', 'updated_at']
    
    def get_board_feet(self, obj):
        return float(obj.board_feet)
    
    def get_inventory(self, obj):
        try:
            inventory = obj.inventory
            return {
                'quantity_pieces': inventory.quantity_pieces,
                'total_board_feet': float(inventory.total_board_feet)
            }
        except Inventory.DoesNotExist:
            return {
                'quantity_pieces': 0,
                'total_board_feet': 0.0
            }


class InventorySerializer(serializers.ModelSerializer):
    product = LumberProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Inventory
        fields = ['id', 'product', 'product_id', 'quantity_pieces', 'total_board_feet', 'last_updated']


class StockTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = StockTransaction
        fields = ['id', 'product', 'product_name', 'transaction_type', 'quantity_pieces', 'board_feet',
                  'reason', 'reference_id', 'cost_per_unit', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']
