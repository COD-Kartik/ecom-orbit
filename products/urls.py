from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import viewsets, permissions
from . import views
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    def get_queryset(self):
        return Product.objects.all()

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet)

urlpatterns = [
    # Dashboard UI
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/products/', views.product_list, name='product_list'),
    path('dashboard/products/add/', views.product_add, name='product_add'),
    path('dashboard/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('dashboard/products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('dashboard/categories/', views.category_list, name='category_list'),
    path('dashboard/categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('dashboard/categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # API
    path('api/', include(router.urls)),
]