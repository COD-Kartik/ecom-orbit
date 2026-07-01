from rest_framework import viewsets, permissions
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Seller only sees their own business products
        user = self.request.user
        if hasattr(user, 'business_profile'):
            return Product.objects.filter(business=user.business_profile)
        return Product.objects.none()

    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business_profile)