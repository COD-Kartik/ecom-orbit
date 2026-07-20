from django.db import models
from accounts.models import BusinessProfile
from products.models import Product

class Channel(models.Model):
    PLATFORM_CHOICES = (
        ('linkedin', 'LinkedIn'),
        ('pinterest', 'Pinterest'),
        ('youtube', 'YouTube'),
        ('flipkart', 'Flipkart'),
        ('whatsapp', 'WhatsApp'),
        ('other', 'Other'),
    )

    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='channels', null=True, blank=True)
    name = models.CharField(max_length=100)
    platform_type = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    api_credentials = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default = True)
    created_at = models.DateTimeField(auto_now_add=True)
    connection_status = models.CharField(max_length=20, default='not_connected')
    last_sync_attempt = models.DateTimeField(blank=True, null=True)
    last_sync_error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.platform_type})"
    

class ProductListing(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='listings')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='listings')
    external_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    published_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.title} → {self.channel.name} ({self.status})"

class SyncLog(models.Model):
    ACTION_CHOICES = (
        ('product_sync', 'Product Sync'),
        ('order_import', 'Order Import'),
    )
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='sync_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    success_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, default='success')  # success, partial, failed
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.channel.name} - {self.action} - {self.created_at}"


class WebhookLog(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='webhook_logs', blank=True, null=True)
    event_type = models.CharField(max_length=50, blank=True)
    raw_payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.event_type or 'Webhook'} - {self.received_at}"