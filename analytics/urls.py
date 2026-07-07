from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/analytics/', views.analytics_view, name='analytics_view'),
]