from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import OrderViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order-api')

urlpatterns = [
    path('dashboard/orders/', views.order_list, name='order_list'),
    path('dashboard/orders/add/', views.order_add, name='order_add'),
    path('dashboard/orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('dashboard/orders/<int:pk>/delete/', views.order_delete, name='order_delete'),
    path('dashboard/orders/<int:pk>/status/', views.order_status_update, name='order_status_update'),
    path('dashboard/orders/<int:pk>/payment/', views.order_payment_update, name='order_payment_update'),
    path('dashboard/orders/export/', views.export_orders_csv, name='export_orders_csv'),
    path('dashboard/customers/', views.customer_list, name='customer_list'),

    path('dashboard/notifications/', views.notifications_view, name='notifications_view'),
    path('dashboard/reports/', views.reports_view, name='reports_view'),
    path('dashboard/reports/export/inventory/', views.export_inventory_csv, name='export_inventory_csv'),
    path('dashboard/reports/export/customers/', views.export_customers_csv, name='export_customers_csv'),

    path('dashboard/marketing/', views.discounts_view, name='discounts_view'),
    path('dashboard/marketing/create/', views.discount_create, name='discount_create'),
    path('dashboard/marketing/<int:pk>/update/', views.discount_update, name='discount_update'),
    path('dashboard/marketing/<int:pk>/delete/', views.discount_delete, name='discount_delete'),

    path('api/', include(router.urls)),
]
    