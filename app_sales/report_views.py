"""
Sales reporting endpoints
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from app_sales.reporting import SalesReports


class SalesReportViewSet(viewsets.ViewSet):
    """API endpoints for sales reports"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        """Get daily sales summary"""
        sales_date = request.query_params.get('date')
        if sales_date:
            from datetime import datetime
            sales_date = datetime.strptime(sales_date, '%Y-%m-%d').date()
        
        report = SalesReports.daily_sales_summary(sales_date)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def top_customers(self, request):
        """Get top customers by sales"""
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))
        
        customers = SalesReports.top_customers(days=days, limit=limit)
        return Response({
            'period_days': days,
            'limit': limit,
            'customers': customers
        })
    
    @action(detail=False, methods=['get'])
    def top_items(self, request):
        """Get top selling items"""
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))
        
        items = SalesReports.top_items(days=days, limit=limit)
        return Response({
            'period_days': days,
            'limit': limit,
            'items': items
        })
    
    @action(detail=False, methods=['get'])
    def income_by_category(self, request):
        """Get income breakdown by category"""
        days = int(request.query_params.get('days', 30))
        
        categories = SalesReports.income_by_category(days=days)
        return Response({
            'period_days': days,
            'categories': categories
        })
    
    @action(detail=False, methods=['get'])
    def senior_pwd_discount(self, request):
        """Get senior/PWD discount summary"""
        days = int(request.query_params.get('days', 30))
        
        summary = SalesReports.senior_pwd_discount_summary(days=days)
        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def credit_outstanding(self, request):
        """Get outstanding credit/SOA balance"""
        days = request.query_params.get('days')
        days = int(days) if days else None
        
        outstanding = SalesReports.credit_sales_outstanding(days=days)
        return Response(outstanding)
    
    @action(detail=False, methods=['get'])
    def sales_trend(self, request):
        """Get sales trend over period"""
        days = int(request.query_params.get('days', 30))
        
        trend = SalesReports.sales_trend(days=days)
        return Response({
            'period_days': days,
            'data': trend
        })
