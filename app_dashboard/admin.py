from django.contrib import admin
from app_dashboard.models import DashboardMetric


@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    list_display = ('metric_type', 'product', 'value', 'threshold', 'recorded_at')
    list_filter = ('metric_type', 'recorded_at')
    readonly_fields = ('recorded_at',)
