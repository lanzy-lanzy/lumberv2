from django.urls import path
from . import views_ui, inventory_pdf_views

app_name = 'round_wood'

urlpatterns = [
    # Dashboard
    path('', views_ui.round_wood_dashboard, name='dashboard'),

    # Round Wood Purchases (Simplified)
    path('purchases/', views_ui.purchase_list, name='purchase_list'),
    path('purchases/create/', views_ui.purchase_create, name='purchase_create'),
    path('purchases/<int:pk>/', views_ui.purchase_detail, name='purchase_detail'),
    path('purchases/<int:pk>/<str:action>/', views_ui.purchase_action, name='purchase_action'),

    # Inventory
    path('inventory/', views_ui.inventory_list, name='inventory_list'),
    path('inventory/export-pdf/', inventory_pdf_views.export_inventory_pdf, name='inventory_export_pdf'),

    # Wood Types
    path('wood-types/', views_ui.wood_types_list, name='wood_types_list'),

    # Walk-in supplier creation
    path('api/create-walkin-supplier/', views_ui.create_walkin_supplier, name='api_create_walkin_supplier'),

    # Wood type creation
    path('api/create-wood-type/', views_ui.create_wood_type, name='api_create_wood_type'),
]
