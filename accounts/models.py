from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('business_owner', 'Business Owner'),
        ('seller', 'Seller'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='seller')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_code_created_at = models.DateTimeField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
class BusinessProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business_profile')
    business_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    address = models.TextField(blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to='business_logos/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    business_phone = models.CharField(max_length=20, blank=True, null=True)
    notifications_last_viewed = models.DateTimeField(blank=True, null=True)
    def __str__(self):
        return self.business_name


class SellerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='sellers')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.business.business_name}"
    
class DismissedNotification(models.Model):
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='dismissed_notifications')
    notif_type = models.CharField(max_length=20)
    reference_id = models.PositiveIntegerField()
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('business', 'notif_type', 'reference_id')

    def __str__(self):
        return f"{self.notif_type} #{self.reference_id} dismissed by {self.business}"