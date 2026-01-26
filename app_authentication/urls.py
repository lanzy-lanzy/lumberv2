from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('admin/pending-registrations/', views.pending_registrations_view, name='pending_registrations'),
    path('admin/pending-registrations/<int:user_id>/approve/', views.approve_registration_view, name='approve_registration'),
    path('admin/pending-registrations/<int:user_id>/reject/', views.reject_registration_view, name='reject_registration'),
    path('admin/users/', views.user_list_view, name='user_list'),
    path('admin/users/customers/', views.customer_user_list_view, name='customer_user_list'),
    path('admin/users/add/', views.add_user_view, name='add_user'),
    path('admin/users/<int:user_id>/toggle-status/', views.toggle_user_status_view, name='toggle_user_status'),
    path('admin/users/<int:user_id>/delete/', views.delete_user_view, name='delete_user'),
]
