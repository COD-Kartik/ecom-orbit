from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='landing'),
    path('features/', views.features_page, name='features_page'),
    path('why-orbit/', views.why_orbit_page, name='why_orbit_page'),
    path('how-it-works/', views.how_it_works_page, name='how_it_works_page'),
    path('pricing/', views.pricing_page, name='pricing_page'),
    path('success-stories/', views.success_stories_page, name='success_stories_page'),
    path('about/', views.about_page, name='about_page'),
    path('contact/', views.contact_page, name='contact_page'),
    path('privacy/', views.privacy_page, name='privacy_page'),
    path('blog/', views.blog_page, name='blog_page'),
    path('terms/', views.terms_page, name='terms_page'),
path('cookies/', views.cookie_policy_page, name='cookie_policy_page'),
]