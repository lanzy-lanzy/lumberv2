from rest_framework import serializers
from app_dashboard.models import DashboardMetric


class DashboardMetricSerializer(serializers.ModelSerializer):
    metric_type_display = serializers.CharField(source='get_metric_type_display', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True, allow_null=True)
    
    class Meta:
        model = DashboardMetric
        fields = ['id', 'metric_type', 'metric_type_display', 'product', 'product_name',
                  'value', 'threshold', 'recorded_at']
