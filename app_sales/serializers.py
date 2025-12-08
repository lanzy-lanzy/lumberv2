from rest_framework import serializers
from app_sales.models import Customer, SalesOrder, SalesOrderItem, Receipt


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone_number', 'address', 'is_senior', 'is_pwd', 'created_at']


class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = SalesOrderItem
        fields = ['id', 'sales_order', 'product', 'product_name', 'quantity_pieces', 
                  'board_feet', 'unit_price', 'subtotal']


class SalesOrderSerializer(serializers.ModelSerializer):
    sales_order_items = SalesOrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = SalesOrder
        fields = ['id', 'so_number', 'customer', 'customer_name', 'total_amount', 'discount', 
                  'discount_amount', 'payment_type', 'amount_paid', 'balance', 'notes',
                  'sales_order_items', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'so_number', 'created_by', 'created_at', 'updated_at']


class ReceiptSerializer(serializers.ModelSerializer):
    sales_order = SalesOrderSerializer(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Receipt
        fields = ['id', 'receipt_number', 'sales_order', 'amount_tendered', 'change',
                  'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['id', 'receipt_number', 'created_by', 'created_at']
