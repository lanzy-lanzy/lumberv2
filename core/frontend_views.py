from django.shortcuts import render, redirect
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
            
            user_role = getattr(request.user, 'role', 'warehouse_staff')
            if user_role not in allowed_roles:
                return HttpResponseForbidden("Access Denied")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Inventory Views
@login_required
@role_required('admin', 'inventory_manager')
def categories(request):
    """Product categories management"""
    context = {
        'page_title': 'Categories',
        'breadcrumbs': ['Inventory', 'Categories'],
    }
    return render(request, 'inventory/categories.html', context)


@login_required
@role_required('admin', 'inventory_manager')
def products(request):
    """Product catalog management"""
    context = {
        'page_title': 'Products',
        'breadcrumbs': ['Inventory', 'Products'],
    }
    return render(request, 'inventory/products.html', context)


@login_required
@role_required('admin', 'inventory_manager')
def stock_in(request):
    """Stock In - Add new inventory"""
    context = {
        'page_title': 'Stock In',
        'breadcrumbs': ['Inventory', 'Stock In'],
    }
    return render(request, 'inventory/stock_in.html', context)


@login_required
@role_required('admin', 'inventory_manager')
def stock_out(request):
    """Stock Out - Record inventory deductions"""
    context = {
        'page_title': 'Stock Out',
        'breadcrumbs': ['Inventory', 'Stock Out'],
    }
    return render(request, 'inventory/stock_out.html', context)


@login_required
@role_required('admin', 'inventory_manager')
def stock_adjustment(request):
    """Stock Adjustment - Inventory corrections"""
    context = {
        'page_title': 'Stock Adjustment',
        'breadcrumbs': ['Inventory', 'Adjustments'],
    }
    return render(request, 'inventory/stock_adjustment.html', context)


# Sales Views
@login_required
@role_required('admin', 'cashier')
def pos(request):
    """Point of Sale interface"""
    context = {
        'page_title': 'Point of Sale',
        'breadcrumbs': ['Sales', 'POS'],
    }
    return render(request, 'sales/pos.html', context)


@login_required
@role_required('admin', 'cashier')
def sales_orders(request):
    """Sales Orders management"""
    context = {
        'page_title': 'Sales Orders',
        'breadcrumbs': ['Sales', 'Orders'],
    }
    return render(request, 'sales/sales_orders.html', context)


# Delivery Views
@login_required
@role_required('admin', 'warehouse_staff')
def delivery_queue(request):
    """Warehouse delivery queue"""
    context = {
        'page_title': 'Delivery Queue',
        'breadcrumbs': ['Delivery', 'Queue'],
    }
    return render(request, 'delivery/delivery_queue.html', context)


@login_required
@role_required('admin', 'warehouse_staff')
def deliveries(request):
    """All deliveries list"""
    context = {
        'page_title': 'All Deliveries',
        'breadcrumbs': ['Delivery', 'All'],
    }
    return render(request, 'delivery/deliveries.html', context)


@login_required
@role_required('admin', 'warehouse_staff')
def all_pickups(request):
    """All pickups list"""
    context = {
        'page_title': 'All Pickups',
        'breadcrumbs': ['Delivery', 'Pickups'],
    }
    return render(request, 'delivery/all_pickups.html', context)


# Supplier Views
@login_required
@role_required('admin', 'inventory_manager')
def suppliers(request):
    """Supplier management"""
    context = {
        'page_title': 'Suppliers',
        'breadcrumbs': ['Supplier', 'List'],
    }
    return render(request, 'supplier/suppliers.html', context)


@login_required
@role_required('admin', 'inventory_manager')
def purchase_orders(request):
    """Purchase Orders management"""
    context = {
        'page_title': 'Purchase Orders',
        'breadcrumbs': ['Supplier', 'POs'],
    }
    return render(request, 'supplier/purchase_orders.html', context)


# Report Views
@login_required
@role_required('admin')
def inventory_reports(request):
    """Inventory reports"""
    context = {
        'page_title': 'Inventory Reports',
        'breadcrumbs': ['Reports', 'Inventory'],
    }
    return render(request, 'reports/inventory_reports.html', context)


@login_required
@role_required('admin')
def sales_reports(request):
    """Sales reports"""
    context = {
        'page_title': 'Sales Reports',
        'breadcrumbs': ['Reports', 'Sales'],
    }
    return render(request, 'reports/sales_reports.html', context)


@login_required
@role_required('admin')
def delivery_reports(request):
    """Delivery reports"""
    context = {
        'page_title': 'Delivery Reports',
        'breadcrumbs': ['Reports', 'Delivery'],
    }
    return render(request, 'reports/delivery_reports.html', context)
