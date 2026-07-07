from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import (
    login_view, logout_view, register_view,
    verify_code_view, resend_verification, demo_dashboard,
    settings_view, update_profile, update_business, change_password, delete_account
)

urlpatterns = [
    path('demo/', demo_dashboard, name='demo_dashboard'),
    path('admin/', admin.site.urls),

  # Auth
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/register/', register_view, name='register'),
    path('auth/verify-code/', verify_code_view, name='verify_code'),
    path('auth/resend-verification/', resend_verification, name='resend_verification'),

    # App modules
    path('', include('products.urls')),
    path('', include('channels_integration.urls')),
    path('', include('orders.urls')),
    path('', include('analytics.urls')),
    path('', include('landing.urls')),

    #settings
    path('dashboard/settings/', settings_view, name='settings'),
    path('dashboard/settings/update-profile/', update_profile, name='update_profile'),
    path('dashboard/settings/update-business/', update_business, name='update_business'),
    path('dashboard/settings/change-password/', change_password, name='change_password'),
    path('dashboard/settings/delete-account/', delete_account, name='delete_account'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)