from django.urls import path
from .views import home, dashboard
from .frontend_views import (
    categories, products, stock_in, stock_out, stock_adjustment,
    pos, sales_orders,
    delivery_queue, deliveries,
    suppliers, purchase_orders,
    inventory_reports, sales_reports, delivery_reports
)
from app_sales.sales_pdf_views import sales_orders_export_preview, export_sales_orders_pdf

urlpatterns = [
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    
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
    
    # Supplier Routes
    path('supplier/suppliers/', suppliers, name='suppliers'),
    path('supplier/purchase-orders/', purchase_orders, name='purchase-orders'),
    
    # Report Routes
    path('reports/inventory/', inventory_reports, name='inventory-reports'),
    path('reports/sales/', sales_reports, name='sales-reports'),
    path('reports/delivery/', delivery_reports, name='delivery-reports'),
]
