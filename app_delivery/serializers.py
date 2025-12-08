from rest_framework import serializers
from app_delivery.models import Delivery, DeliveryLog


class DeliveryLogSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    
    class Meta:
        model = DeliveryLog
        fields = ['id', 'delivery', 'status', 'notes', 'updated_by', 'updated_by_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class DeliverySerializer(serializers.ModelSerializer):
    delivery_logs = DeliveryLogSerializer(many=True, read_only=True)
    sales_order_number = serializers.CharField(source='sales_order.so_number', read_only=True)
    
    class Meta:
        model = Delivery
        fields = ['id', 'delivery_number', 'sales_order', 'sales_order_number', 'status',
                  'driver_name', 'plate_number', 'customer_signature', 'delivery_logs',
                  'created_at', 'updated_at', 'delivered_at']
        read_only_fields = ['id', 'delivery_number', 'created_at', 'updated_at']
