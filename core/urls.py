from django.urls import path
from .views import home, dashboard, customer_dashboard
from .customer_views import (
    customer_browse_products, customer_product_detail, 
    customer_my_orders, customer_order_detail, customer_profile,
    customer_shopping_cart
)
from .frontend_views import (
    categories, products, stock_in, stock_out, stock_adjustment,
    pos, sales_orders,
    delivery_queue, deliveries, all_pickups,
    suppliers, purchase_orders,
    inventory_reports, sales_reports
)
from app_sales.sales_pdf_views import sales_orders_export_preview, export_sales_orders_pdf
from app_sales.report_pdf_views import export_sales_report_pdf
from app_dashboard.views import (
    low_stock_alerts_view, aged_receivables_view, inventory_composition_view,
    sales_trend_view, supplier_totals_view
)

urlpatterns = [
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('customer/dashboard/', customer_dashboard, name='customer-dashboard'),
    path('customer/products/', customer_browse_products, name='customer-browse-products'),
    path('customer/products/<int:product_id>/', customer_product_detail, name='customer-product-detail'),
    path('customer/orders/', customer_my_orders, name='customer-my-orders'),
    path('customer/orders/<int:order_id>/', customer_order_detail, name='customer-order-detail'),
    path('customer/profile/', customer_profile, name='customer-profile'),
    path('customer/cart/', customer_shopping_cart, name='customer-shopping-cart'),
    
    # Inventory Routes
    path('inventory/categories/', categories, name='categories'),
    path('inventory/products/', products, name='products'),
    path('inventory/stock-in/', stock_in, name='stock-in'),
    path('inventory/stock-out/', stock_out, name='stock-out'),
    path('inventory/adjustments/', stock_adjustment, name='stock-adjustment'),
    
    # Sales Routes
    path('sales/pos/', pos, name='pos'),
    path('sales/orders/', sales_orders, name='sales-orders'),
    path('sales/orders/export/preview/', sales_orders_export_preview, name='sales-orders-export-preview'),
    path('sales/orders/export/pdf/', export_sales_orders_pdf, name='sales-orders-export-pdf'),
    
    # Delivery Routes
    path('delivery/queue/', delivery_queue, name='delivery-queue'),
    path('delivery/all/', deliveries, name='deliveries'),
    path('delivery/pickups/', all_pickups, name='all-pickups'),
    
    # Supplier Routes
    path('supplier/suppliers/', suppliers, name='suppliers'),
    path('supplier/purchase-orders/', purchase_orders, name='purchase-orders'),
    
    # Report Routes
    path('reports/inventory/', inventory_reports, name='inventory-reports'),
    path('reports/sales/', sales_reports, name='sales-reports'),
    path('reports/sales/export/pdf/', export_sales_report_pdf, name='sales-reports-export-pdf'),
    
    # Dashboard Partials Routes
    path('dashboard/low_stock_alerts/', low_stock_alerts_view, name='dashboard-low-stock-alerts'),
    path('dashboard/aged_receivables/', aged_receivables_view, name='dashboard-aged-receivables'),
    path('dashboard/inventory_composition/', inventory_composition_view, name='dashboard-inventory-composition'),
    path('dashboard/sales_trend/', sales_trend_view, name='dashboard-sales-trend'),
    path('dashboard/supplier_totals/', supplier_totals_view, name='dashboard-supplier-totals'),
]
