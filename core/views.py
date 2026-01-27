from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from functools import wraps
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from core.models import CustomUser
from core.serializers import UserSerializer, UserCreateSerializer


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


@require_http_methods(["GET"])
def home(request):
    """Landing page - main entry point"""
    # If user is authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Show landing page to unauthenticated users
    context = {}
    return render(request, 'landing.html', context)


@never_cache
@login_required
@require_http_methods(["GET"])
def dashboard(request):
    """Dashboard page - employees only"""
    # Refresh user from database to ensure clean session state
    request.user.refresh_from_db()
    
    # Customers should not access this view - redirect them
    if request.user.is_customer():
        return redirect('customer-dashboard')
    
    # Check if user has a valid role, if not set default
    if not request.user.role and request.user.is_employee():
        request.user.role = 'warehouse_staff'
        request.user.save()
    
    # Employee dashboard
    context = {
        'user': request.user,
        'user_role': request.user.role,
    }
    return render(request, 'dashboard.html', context)


@never_cache
@login_required
@require_http_methods(["GET"])
def customer_dashboard(request):
    """Customer dashboard view - customers only"""
    import sys
    print(f"DEBUG: customer_dashboard accessed", file=sys.stderr)
    print(f"DEBUG: user={request.user.username}, is_authenticated={request.user.is_authenticated}", file=sys.stderr)
    print(f"DEBUG: is_customer={request.user.is_customer()}", file=sys.stderr)
    
    # Refresh user from database to ensure clean session state
    request.user.refresh_from_db()
    
    # Only allow customers
    if not request.user.is_customer():
        print(f"DEBUG: User is not a customer, redirecting to dashboard", file=sys.stderr)
        return redirect('dashboard')
    
    print(f"DEBUG: Rendering customer dashboard", file=sys.stderr)
    
    from app_sales.models import SalesOrder
    from app_sales.services import SalesService
    from django.db.models import Sum, Count
    
    # Get customer's sales orders if they have a linked customer record
    sales_orders = SalesOrder.objects.none()
    total_spent = 0
    order_count = 0
    
    try:
        # Use unified lookup logic from SalesService
        sales_customer = SalesService.get_customer_for_user(request.user)
        
        if sales_customer:
            sales_orders = sales_customer.sales_orders.all().order_by('-created_at')[:10]
            stats = sales_customer.sales_orders.aggregate(
                total=Sum('total_amount'),
                count=Count('id')
            )
            total_spent = stats['total'] or 0
            order_count = stats['count'] or 0
    except Exception as e:
        print(f"DEBUG: Exception in customer_dashboard: {e}", file=sys.stderr)
        pass
    
    context = {
        'user': request.user,
        'customer_profile': getattr(request.user, 'customer_profile', None),
        'sales_orders': sales_orders,
        'total_spent': total_spent,
        'order_count': order_count,
    }
    return render(request, 'customer/dashboard.html', context)


class UserViewSet(viewsets.ModelViewSet):
    """API endpoint for user management"""
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user information"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """Get users by role"""
        role = request.query_params.get('role')
        if not role:
            return Response({'error': 'role parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        users = CustomUser.objects.filter(role=role)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)


# Frontend Views - Inventory

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


# Frontend Views - Sales

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


# Frontend Views - Delivery

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


# Frontend Views - Supplier

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


# Frontend Views - Reports

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
