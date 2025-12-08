# Add this view to your core/views.py or create a new landing app

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def landing(request):
    """Landing page - no authentication required"""
    context = {
        'page_title': 'Lumber Management System - Streamline Your Inventory',
    }
    return render(request, 'landing.html', context)

# Add to your main urls.py (lumber/urls.py):
# 
# from django.urls import path
# from . import views
#
# urlpatterns = [
#     # ... existing patterns ...
#     
#     # Landing page (public)
#     path('', views.landing, name='landing'),
#     path('home/', views.landing, name='home'),
#     
#     # ... rest of patterns ...
# ]

# Or for root URL in project urls.py:
#
# from django.urls import path
# from core import views
#
# urlpatterns = [
#     path('', views.landing, name='landing'),
#     # ... other patterns ...
# ]
