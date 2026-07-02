from django.contrib import admin
from .models import Channel, ProductListing

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform_type', 'business', 'is_active', 'created_at')
    list_filter = ('platform_type', 'is_active')
    search_fields = ('name',)

@admin.register(ProductListing)
class ProductListingAdmin(admin.ModelAdmin):
    list_display = ('product', 'channel', 'status', 'published_at')
    list_filter = ('status', 'channel')