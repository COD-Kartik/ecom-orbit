from django.contrib import admin
from .models import Channel, ProductListing, SyncLog, WebhookLog

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform_type', 'business', 'is_active', 'created_at')
    list_filter = ('platform_type', 'is_active')
    search_fields = ('name',)

@admin.register(ProductListing)
class ProductListingAdmin(admin.ModelAdmin):
    list_display = ('product', 'channel', 'status', 'published_at')
    list_filter = ('status', 'channel')

@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('channel', 'action', 'status', 'success_count', 'failed_count', 'created_at')
    list_filter = ('action', 'status', 'channel')
    readonly_fields = ('error_detail',)
    
@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ('channel', 'event_type', 'received_at')
    list_filter = ('event_type', 'channel')