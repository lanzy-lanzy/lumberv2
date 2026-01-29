import os
import django

# Setup Django before importing REST framework
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lumber.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from app_inventory.views import LumberProductViewSet

def debug_api():
    User = get_user_model()
    admin = User.objects.filter(is_superuser=True).first()
    
    factory = APIRequestFactory()
    # Test with different page sizes
    for page_size in [10, 100, 1000]:
        request = factory.get(f'/api/products/?page_size={page_size}')
        if admin:
            from rest_framework.test import force_authenticate
            force_authenticate(request, user=admin)
            
        view = LumberProductViewSet.as_view({'get': 'list'})
        response = view(request)
        
        print(f"\n--- Testing with page_size={page_size} ---")
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.data)
            continue
            
        data = response.data
        results = data.get('results', [])
        count = data.get('count', 0)
        print(f"Total count in DB: {count}")
        print(f"Results returned: {len(results)}")
        
        for p in results:
            inv = p.get('inventory')
            pcs = inv.get('quantity_pieces') if inv else 'N/A'
            bf = inv.get('total_board_feet') if inv else 'N/A'
            print(f"Product: {p['name']}, Active: {p['is_active']}, Pieces: {pcs}, BF: {bf}")

if __name__ == "__main__":
    debug_api()
