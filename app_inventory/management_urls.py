from django.urls import path
from app_inventory import management_views

app_name = 'inventory_management'

urlpatterns = [
    # Main dashboard
    path('', management_views.inventory_management_dashboard, name='dashboard'),
    
    # Management views
    path('categories/', management_views.categories_management, name='categories'),
    path('products/', management_views.products_management, name='products'),
    path('stock-in/', management_views.stock_in_management, name='stock_in'),
    path('stock-out/', management_views.stock_out_management, name='stock_out'),
    path('inventory-levels/', management_views.inventory_levels, name='inventory_levels'),
    path('transaction-history/', management_views.transaction_history, name='transaction_history'),
    
    # PDF Exports
    path('export/inventory-pdf/', management_views.export_inventory_pdf, name='export_inventory_pdf'),
    path('export/transactions-pdf/', management_views.export_stock_transactions_pdf, name='export_transactions_pdf'),
    path('export/products-pdf/', management_views.export_products_pdf, name='export_products_pdf'),
    path('export/categories-pdf/', management_views.export_category_summary_pdf, name='export_categories_pdf'),
    path('export/report-pdf/', management_views.export_inventory_report_pdf, name='export_report_pdf'),
]
