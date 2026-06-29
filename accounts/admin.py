from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, BusinessProfile, SellerProfile

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'phone')}),
    )

@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('business_name',)}

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'business', 'is_active', 'created_at')
    list_filter = ('is_active',)