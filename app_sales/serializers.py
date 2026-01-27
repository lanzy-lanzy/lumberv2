from rest_framework import serializers
from app_sales.models import Customer, SalesOrder, SalesOrderItem, Receipt, ShoppingCart, CartItem
from app_inventory.models import LumberProduct


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone_number', 'address', 'created_at']


class SalesOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_category_name = serializers.CharField(source='product.category.name', read_only=True)
    product_category_id = serializers.IntegerField(source='product.category.id', read_only=True)
    
    class Meta:
        model = SalesOrderItem
        fields = ['id', 'sales_order', 'product', 'product_name', 'product_category_name',
                  'product_category_id', 'quantity_pieces', 'board_feet', 'unit_price', 'subtotal']


class SalesOrderSerializer(serializers.ModelSerializer):
    confirmed_by_name = serializers.CharField(source='confirmed_by.get_full_name', read_only=True)
    sales_order_items = SalesOrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    confirmation_status = serializers.SerializerMethodField()
    order_source_display = serializers.CharField(source='get_order_source_display', read_only=True)
    
    class Meta:
        model = SalesOrder
        fields = ['id', 'so_number', 'customer', 'customer_name', 'total_amount', 'discount', 
                  'discount_amount', 'payment_type', 'amount_paid', 'balance', 'notes',
                  'sales_order_items', 'created_by', 'created_by_name', 'created_at', 'updated_at',
                  'confirmation_status', 'order_source', 'order_source_display',
                  'is_confirmed', 'confirmed_at', 'confirmed_by', 'confirmed_by_name']
        read_only_fields = ['id', 'so_number', 'created_by', 'created_at', 'updated_at', 
                            'confirmation_status', 'order_source_display', 'is_confirmed', 
                            'confirmed_at', 'confirmed_by']
    
    def get_confirmation_status(self, obj):
        """Get the confirmation status for this order"""
        if hasattr(obj, 'confirmation'):
            return obj.confirmation.status
        return None


class ReceiptSerializer(serializers.ModelSerializer):
    sales_order = SalesOrderSerializer(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Receipt
        fields = ['id', 'receipt_number', 'sales_order', 'amount_tendered', 'change',
                  'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['id', 'receipt_number', 'created_by', 'created_at']


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_image = serializers.SerializerMethodField(read_only=True)
    price = serializers.SerializerMethodField(read_only=True)
    subtotal = serializers.SerializerMethodField(read_only=True)
    available_quantity = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'product', 'product_name', 'product_sku', 'product_image',
                  'quantity', 'price', 'subtotal', 'available_quantity', 'added_at', 'updated_at']
        read_only_fields = ['id', 'product', 'added_at', 'updated_at']
    
    def get_product_image(self, obj):
        if obj.product.image:
            return obj.product.image.url
        return None
    
    def get_price(self, obj):
        return float(obj.get_price())
    
    def get_subtotal(self, obj):
        return float(obj.get_subtotal())
    
    def get_available_quantity(self, obj):
        inventory = getattr(obj.product, 'inventory', None)
        return inventory.quantity_pieces if inventory else 0


class ShoppingCartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField(read_only=True)
    total_items = serializers.SerializerMethodField(read_only=True)
    item_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = ShoppingCart
        fields = ['id', 'items', 'total', 'total_items', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total(self, obj):
        return float(obj.get_total())
    
    def get_total_items(self, obj):
        return obj.get_total_items()
    
    def get_item_count(self, obj):
        return obj.get_item_count()
