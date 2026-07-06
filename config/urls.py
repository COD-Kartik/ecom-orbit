from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import (
    landing_page, login_view, logout_view,
    register_view, register_business, register_seller
)

urlpatterns = [
    path('', landing_page, name='landing'),
    path('admin/', admin.site.urls),

    # Auth
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/register/', register_view, name='register'),
    path('auth/register/business/', register_business, name='register_business'),
    path('auth/register/seller/', register_seller, name='register_seller'),

    # Google OAuth
    path('auth/social/', include('social_django.urls', namespace='social')),

    # App modules
    path('', include('products.urls')),
    path('', include('channels_integration.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)