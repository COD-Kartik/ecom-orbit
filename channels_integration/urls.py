from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChannelViewSet, ProductListingViewSet
from . import views

router = DefaultRouter()
router.register(r'channels', ChannelViewSet, basename='channel-api')
router.register(r'listings', ProductListingViewSet, basename='listing-api')

urlpatterns = [
    # Channel UI
    path('dashboard/channels/', views.channel_list, name='channel_list'),
    path('dashboard/channels/<int:pk>/delete/', views.channel_delete, name='channel_delete'),
    path('dashboard/channels/<int:pk>/toggle/', views.channel_toggle, name='channel_toggle'),
    # Listings UI
    path('dashboard/listings/', views.listing_list, name='listing_list'),
    path('dashboard/listings/<int:pk>/delete/', views.listing_delete, name='listing_delete'),
    path('dashboard/listings/<int:pk>/status/', views.listing_status_update, name='listing_status_update'),
    # Publishing
    path('dashboard/products/<int:product_id>/publish/', views.publish_product, name='publish_product'),
    path('dashboard/products/<int:product_id>/select-channels/', views.select_channels_to_publish, name='select_channels_to_publish'),
    # API
    path('api/', include(router.urls)),
]