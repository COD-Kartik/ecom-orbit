from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import viewsets, permissions
from . import views
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from .views import get_user_business


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Product.objects.filter(business=business) if business else Product.objects.none()

    def perform_create(self, serializer):
        business = get_user_business(self.request.user)
        serializer.save(business=business)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Category.objects.filter(business=business) if business else Category.objects.none()

    def perform_create(self, serializer):
        business = get_user_business(self.request.user)
        serializer.save(business=business)


router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')

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