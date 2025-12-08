# Frontend URL Configuration for Phase 7
# Add these to your main lumber/urls.py file

"""
Example integration in lumber/urls.py:

from django.urls import path, include
from . import views as frontend_views

urlpatterns = [
    # ... existing patterns ...
    
    # Frontend Dashboard Routes
    path('dashboard/', frontend_views.dashboard, name='dashboard'),
    
    # Inventory Routes
    path('inventory/products/', frontend_views.products, name='products'),
    path('inventory/dashboard/', frontend_views.inventory_dashboard, name='inventory-dashboard'),
    path('inventory/stock-in/', frontend_views.stock_in, name='stock-in'),
    path('inventory/stock-out/', frontend_views.stock_out, name='stock-out'),
    path('inventory/adjustments/', frontend_views.stock_adjustment, name='stock-adjustment'),
    
    # Sales Routes
    path('sales/pos/', frontend_views.pos, name='pos'),
    path('sales/orders/', frontend_views.sales_orders, name='sales-orders'),
    
    # Delivery Routes
    path('delivery/queue/', frontend_views.delivery_queue, name='delivery-queue'),
    path('delivery/all/', frontend_views.deliveries, name='deliveries'),
    
    # Supplier Routes
    path('supplier/suppliers/', frontend_views.suppliers, name='suppliers'),
    path('supplier/purchase-orders/', frontend_views.purchase_orders, name='purchase-orders'),
    
    # Report Routes
    path('reports/inventory/', frontend_views.inventory_reports, name='inventory-reports'),
    path('reports/sales/', frontend_views.sales_reports, name='sales-reports'),
    path('reports/delivery/', frontend_views.delivery_reports, name='delivery-reports'),
]
"""

# Here's the views.py implementation

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from functools import wraps


def role_required(*allowed_roles):
    """Decorator to check user role"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            user_role = getattr(request.user, 'role', 'User')
            if user_role not in allowed_roles:
                return HttpResponseForbidden("Access Denied")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Dashboard Views
@login_required
def dashboard(request):
    """Main dashboard - routes to role-specific dashboard"""
    context = {
        'user': request.user,
        'user_role': getattr(request.user, 'role', 'User'),
    }
    return render(request, 'dashboard.html', context)


# Inventory Views
@login_required
@role_required('Admin', 'Inventory Manager')
def products(request):
    """Product catalog management"""
    context = {
        'page_title': 'Products',
        'breadcrumbs': ['Inventory', 'Products'],
    }
    return render(request, 'inventory/products.html', context)


@login_required
@role_required('Admin', 'Inventory Manager')
def inventory_dashboard(request):
    """Inventory manager dashboard"""
    context = {
        'page_title': 'Inventory Dashboard',
        'breadcrumbs': ['Dashboard', 'Inventory'],
    }
    return render(request, 'dashboards/inventory_manager_dashboard.html', context)


@login_required
@role_required('Admin', 'Inventory Manager')
def stock_in(request):
    """Stock In - Add new inventory"""
    context = {
        'page_title': 'Stock In',
        'breadcrumbs': ['Inventory', 'Stock In'],
    }
    return render(request, 'inventory/stock_in.html', context)


@login_required
@role_required('Admin', 'Inventory Manager')
def stock_out(request):
    """Stock Out - Record inventory deductions"""
    context = {
        'page_title': 'Stock Out',
        'breadcrumbs': ['Inventory', 'Stock Out'],
    }
    return render(request, 'inventory/stock_out.html', context)


@login_required
@role_required('Admin', 'Inventory Manager')
def stock_adjustment(request):
    """Stock Adjustment - Inventory corrections"""
    context = {
        'page_title': 'Stock Adjustment',
        'breadcrumbs': ['Inventory', 'Adjustments'],
    }
    return render(request, 'inventory/stock_adjustment.html', context)


# Sales Views
@login_required
@role_required('Admin', 'Cashier')
def pos(request):
    """Point of Sale interface"""
    context = {
        'page_title': 'Point of Sale',
        'breadcrumbs': ['Sales', 'POS'],
    }
    return render(request, 'dashboards/cashier_dashboard.html', context)


@login_required
@role_required('Admin', 'Cashier')
def sales_orders(request):
    """Sales Orders management"""
    context = {
        'page_title': 'Sales Orders',
        'breadcrumbs': ['Sales', 'Orders'],
    }
    return render(request, 'sales/sales_orders.html', context)


# Delivery Views
@login_required
@role_required('Admin', 'Warehouse Staff')
def delivery_queue(request):
    """Warehouse delivery queue"""
    context = {
        'page_title': 'Delivery Queue',
        'breadcrumbs': ['Delivery', 'Queue'],
    }
    return render(request, 'dashboards/warehouse_dashboard.html', context)


@login_required
@role_required('Admin', 'Warehouse Staff')
def deliveries(request):
    """All deliveries list"""
    context = {
        'page_title': 'All Deliveries',
        'breadcrumbs': ['Delivery', 'All'],
    }
    return render(request, 'delivery/deliveries.html', context)


# Supplier Views
@login_required
@role_required('Admin', 'Inventory Manager')
def suppliers(request):
    """Supplier management"""
    context = {
        'page_title': 'Suppliers',
        'breadcrumbs': ['Supplier', 'List'],
    }
    return render(request, 'supplier/suppliers.html', context)


@login_required
@role_required('Admin', 'Inventory Manager')
def purchase_orders(request):
    """Purchase Orders management"""
    context = {
        'page_title': 'Purchase Orders',
        'breadcrumbs': ['Supplier', 'POs'],
    }
    return render(request, 'supplier/purchase_orders.html', context)


# Report Views
@login_required
@role_required('Admin')
def inventory_reports(request):
    """Inventory reports"""
    context = {
        'page_title': 'Inventory Reports',
        'breadcrumbs': ['Reports', 'Inventory'],
    }
    return render(request, 'reports/inventory_reports.html', context)


@login_required
@role_required('Admin')
def sales_reports(request):
    """Sales reports"""
    context = {
        'page_title': 'Sales Reports',
        'breadcrumbs': ['Reports', 'Sales'],
    }
    return render(request, 'reports/sales_reports.html', context)


@login_required
@role_required('Admin')
def delivery_reports(request):
    """Delivery reports"""
    context = {
        'page_title': 'Delivery Reports',
        'breadcrumbs': ['Reports', 'Delivery'],
    }
    return render(request, 'reports/delivery_reports.html', context)
