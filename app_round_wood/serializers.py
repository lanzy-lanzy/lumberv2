from rest_framework import serializers
from .models import WoodType, RoundWoodPurchase, RoundWoodInventory


class WoodTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WoodType
        fields = [
            'id', 'name', 'species', 'description',
            'default_diameter_inches', 'default_length_feet',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class RoundWoodPurchaseSerializer(serializers.ModelSerializer):
    """Serializer for simplified round wood purchases"""
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    wood_type_name = serializers.CharField(source='wood_type.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = RoundWoodPurchase
        fields = [
            'id', 'supplier', 'supplier_name', 'wood_type', 'wood_type_name',
            'quantity_logs', 'diameter_inches', 'length_feet',
            'volume_cubic_feet', 'unit_cost_per_board_feet', 'total_cost',
            'status', 'purchase_date', 'notes',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['board_feet', 'volume_cubic_feet', 'total_cost', 'created_by', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate purchase data"""
        diameter = data.get('diameter_inches')
        length = data.get('length_feet')
        quantity = data.get('quantity_logs')
        
        if diameter is not None and length is not None and quantity is not None:
            if diameter <= 0:
                raise serializers.ValidationError({'diameter_inches': 'Diameter must be greater than 0'})
            if length <= 0:
                raise serializers.ValidationError({'length_feet': 'Length must be greater than 0'})
            if quantity < 1:
                raise serializers.ValidationError({'quantity_logs': 'Quantity must be at least 1'})
        
        return data


class RoundWoodInventorySerializer(serializers.ModelSerializer):
    """Serializer for inventory"""
    wood_type_name = serializers.CharField(source='wood_type.name', read_only=True)
    wood_type_species = serializers.CharField(source='wood_type.get_species_display', read_only=True)
    
    class Meta:
        model = RoundWoodInventory
        fields = [
            'id', 'wood_type', 'wood_type_name', 'wood_type_species',
            'total_logs_in_stock', 'total_cubic_feet_in_stock',
            'total_cost_invested', 'average_cost_per_cubic_foot',
            'warehouse_location', 'last_stock_in_date', 'last_updated'
        ]
        read_only_fields = [
            'total_logs_in_stock', 'total_cubic_feet_in_stock',
            'total_cost_invested', 'average_cost_per_cubic_foot',
            'last_stock_in_date', 'last_updated'
        ]
