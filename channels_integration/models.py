from django.db import models
from accounts.models import BusinessProfile
from products.models import Product

class Channel(models.Model):
    PLATFORM_CHOICES = (
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
        ('linkedin', 'LinkedIn'),
        ('pinterest', 'Pinterest'),
        ('youtube', 'YouTube'),
        ('other', 'Other'),
    )

    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='channels', null=True, blank=True)
    name = models.CharField(max_length=100)
    platform_type = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    api_credentials = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default = True)
    created_at = models.DateTimeField(auto_now_add=True)

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
