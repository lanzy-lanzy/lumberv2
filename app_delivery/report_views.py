"""
Delivery reporting endpoints
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from app_delivery.reporting import DeliveryReports


class DeliveryReportViewSet(viewsets.ViewSet):
    """API endpoints for delivery reports"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        """Get daily delivery summary"""
        summary_date = request.query_params.get('date')
        if summary_date:
            from datetime import datetime
            summary_date = datetime.strptime(summary_date, '%Y-%m-%d').date()
        
        report = DeliveryReports.daily_delivery_summary(summary_date)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def turnaround_time(self, request):
        """Get delivery turnaround time analysis"""
        days = int(request.query_params.get('days', 30))
        
        report = DeliveryReports.delivery_turnaround_time(days=days)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def by_driver(self, request):
        """Get delivery statistics by driver"""
        days = int(request.query_params.get('days', 30))
        
        drivers = DeliveryReports.delivery_by_driver(days=days)
        return Response({
            'period_days': days,
            'drivers': drivers
        })
    
    @action(detail=False, methods=['get'])
    def failure_analysis(self, request):
        """Get delivery failures and stuck orders"""
        days = int(request.query_params.get('days', 30))
        
        failures = DeliveryReports.delivery_failures(days=days)
        return Response({
            'period_days': days,
            'stuck_deliveries': len(failures),
            'deliveries': failures
        })
    
    @action(detail=False, methods=['get'])
    def volume_trend(self, request):
        """Get delivery volume trend"""
        days = int(request.query_params.get('days', 30))
        
        trend = DeliveryReports.delivery_volume_trend(days=days)
        return Response({
            'period_days': days,
            'data': trend
        })
    
    @action(detail=False, methods=['get'])
    def vehicle_utilization(self, request):
        """Get vehicle/driver utilization metrics"""
        days = int(request.query_params.get('days', 30))
        
        utilization = DeliveryReports.vehicle_utilization(days=days)
        return Response(utilization)
