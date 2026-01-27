"""
Delivery reporting and analytics
"""
from decimal import Decimal
from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta, date
from app_delivery.models import Delivery, DeliveryLog
from app_sales.models import SalesOrder


class DeliveryReports:
    """Generate delivery reports"""
    
    @staticmethod
    def daily_delivery_summary(summary_date=None):
        """
        Get daily delivery summary
        
        Args:
            summary_date: Date to report on (default: today)
            
        Returns:
            Dict with daily delivery data
        """
        if not summary_date:
            summary_date = timezone.now().date()
        
        deliveries = Delivery.objects.filter(created_at__date=summary_date)
        
        delivered = deliveries.filter(status='delivered', delivered_at__date=summary_date).count()
        pending = deliveries.filter(status='pending').count()
        in_progress = deliveries.filter(status__in=['on_picking', 'loaded']).count()
        in_transit = deliveries.filter(status='out_for_delivery').count()
        
        # Calculate metrics
        delivered_today = Delivery.objects.filter(
            status='delivered',
            delivered_at__date=summary_date
        )
        
        avg_time = None
        if delivered_today.exists():
            times = []
            for d in delivered_today:
                if d.delivered_at:
                    time_taken = (d.delivered_at - d.created_at).total_seconds() / 3600
                    times.append(time_taken)
            if times:
                avg_time = sum(times) / len(times)
        
        return {
            'date': summary_date,
            'deliveries_created': deliveries.count(),
            'delivered_today': delivered,
            'pending': pending,
            'in_progress': in_progress,
            'in_transit': in_transit,
            'avg_delivery_time_hours': round(avg_time, 1) if avg_time else None,
            'completion_rate': round((delivered / deliveries.count() * 100), 1) if deliveries.count() > 0 else 0
        }
    
    @staticmethod
    def delivery_turnaround_time(days=30):
        """
        Get delivery turnaround time analysis
        
        Args:
            days: Period in days
            
        Returns:
            Dict with turnaround metrics
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        completed = Delivery.objects.filter(
            status='delivered',
            delivered_at__gte=cutoff_date,
            delivered_at__isnull=False
        )
        
        times = []
        for d in completed:
            time_taken = (d.delivered_at - d.created_at).total_seconds() / 3600
            times.append(time_taken)
        
        if not times:
            return {
                'period_days': days,
                'completed_deliveries': 0,
                'avg_turnaround_hours': None,
                'min_turnaround_hours': None,
                'max_turnaround_hours': None,
                'median_turnaround_hours': None
            }
        
        times.sort()
        median = times[len(times) // 2]
        
        return {
            'period_days': days,
            'completed_deliveries': len(times),
            'avg_turnaround_hours': round(sum(times) / len(times), 1),
            'min_turnaround_hours': round(min(times), 1),
            'max_turnaround_hours': round(max(times), 1),
            'median_turnaround_hours': round(median, 1)
        }
    
    @staticmethod
    def delivery_by_driver(days=30):
        """
        Get delivery statistics by driver
        
        Args:
            days: Period in days
            
        Returns:
            List of driver statistics
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        drivers = Delivery.objects.filter(
            created_at__gte=cutoff_date,
            status='delivered',
            driver_name__isnull=False
        ).values('driver_name').annotate(
            deliveries=Count('id'),
            total_bf=Sum('sales_order__sales_order_items__board_feet')
        ).order_by('-deliveries')
        
        return list(drivers)
    
    @staticmethod
    def delivery_failures(days=30):
        """
        Get delivery failures and issues
        
        Args:
            days: Period in days
            
        Returns:
            List of failed/problematic deliveries
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Deliveries stuck in transit or pending for too long
        pending_too_long = Delivery.objects.filter(
            status__in=['pending', 'on_picking', 'loaded', 'out_for_delivery'],
            created_at__lte=cutoff_date
        ).select_related('sales_order', 'sales_order__customer')
        
        issues = []
        for d in pending_too_long:
            age_hours = (timezone.now() - d.created_at).total_seconds() / 3600
            issues.append({
                'delivery_id': d.id,
                'delivery_number': d.delivery_number,
                'so_number': d.sales_order.so_number,
                'customer': d.sales_order.customer.name,
                'status': d.status,
                'age_hours': round(age_hours, 1),
                'created_at': d.created_at
            })
        
        # Sort by age descending
        issues.sort(key=lambda x: x['age_hours'], reverse=True)
        return issues
    
    @staticmethod
    def delivery_volume_trend(days=30):
        """
        Get delivery volume trend over time
        
        Args:
            days: Period in days
            
        Returns:
            List of daily volume data
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        volumes = Delivery.objects.filter(
            created_at__gte=cutoff_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            created=Count('id', filter=Q(status__in=['pending', 'on_picking', 'loaded', 'out_for_delivery', 'delivered'])),
            completed=Count('id', filter=Q(status='delivered')),
            in_progress=Count('id', filter=Q(status__in=['on_picking', 'loaded', 'out_for_delivery']))
        ).order_by('date')
        
        return list(volumes)
    
    @staticmethod
    def vehicle_utilization(days=30):
        """
        Get vehicle/driver utilization metrics
        
        Args:
            days: Period in days
            
        Returns:
            Dict with utilization data
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        out_for_delivery = Delivery.objects.filter(
            status='out_for_delivery',
            created_at__gte=cutoff_date
        )
        
        vehicles = out_for_delivery.values('plate_number').annotate(
            deliveries=Count('id'),
            driver=F('driver_name')
        ).distinct()
        
        total_deliveries = out_for_delivery.count()
        unique_vehicles = out_for_delivery.values('plate_number').distinct().count()
        
        return {
            'period_days': days,
            'total_active_deliveries': total_deliveries,
            'unique_vehicles': unique_vehicles,
            'avg_deliveries_per_vehicle': round(total_deliveries / unique_vehicles, 1) if unique_vehicles > 0 else 0,
            'vehicles': list(vehicles)
        }
