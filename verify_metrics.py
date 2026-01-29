import os
import django

# Setup Django before importing REST framework
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lumber.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from app_dashboard.views import DashboardMetricViewSet

def verify_metrics():
    User = get_user_model()
    admin = User.objects.filter(is_superuser=True).first()
    
    factory = APIRequestFactory()
    request = factory.get('/api/metrics/executive_dashboard/')
    if admin:
        from rest_framework.test import force_authenticate
        force_authenticate(request, user=admin)
        
    view = DashboardMetricViewSet.as_view({'get': 'executive_dashboard'})
    response = view(request)
    
    print("\n--- Executive Dashboard Metrics ---")
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.data)
        return
        
    data = response.data
    inv = data.get('inventory', {})
    print(f"Total Pieces: {inv.get('total_pieces')}")
    print(f"Total Board Feet: {inv.get('total_board_feet')}")
    print(f"Total Value: PHP {inv.get('total_value'):,.2f}")
    
    # Check products list for pagination
    from app_inventory.views import LumberProductViewSet
    request = factory.get('/api/products/')
    if admin:
        from rest_framework.test import force_authenticate
        force_authenticate(request, user=admin)
    view = LumberProductViewSet.as_view({'get': 'list'})
    response = view(request)
    print(f"\nProducts List (Default): {len(response.data.get('results', []))} items returned (Total Count: {response.data.get('count')})")

if __name__ == "__main__":
    verify_metrics()
