from rest_framework import serializers
from app_supplier.models import Supplier, PurchaseOrder, PurchaseOrderItem, SupplierPriceHistory


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'company_name', 'contact_person', 'email', 'phone_number', 'address',
                  'delivery_speed_rating', 'is_active', 'created_at', 'updated_at']


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'purchase_order', 'product', 'product_name', 'quantity_pieces',
                  'cost_per_unit', 'subtotal']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    po_items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = ['id', 'po_number', 'supplier', 'supplier_name', 'status', 'expected_delivery_date',
                  'total_amount', 'notes', 'po_items', 'created_by', 'created_by_name',
                  'created_at', 'updated_at', 'received_at']
        read_only_fields = ['id', 'po_number', 'created_by', 'created_at', 'updated_at']


class SupplierPriceHistorySerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = SupplierPriceHistory
        fields = ['id', 'supplier', 'supplier_name', 'product', 'product_name',
                  'price_per_unit', 'valid_from', 'valid_to', 'created_at']
