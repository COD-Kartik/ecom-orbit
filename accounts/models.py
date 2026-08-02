from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('business_owner', 'Business Owner'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='business_owner')
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
    PLAN_CHOICES = (
    ('free', 'Free Plan'),
    ('starter', 'Starter'),
    ('pro', 'Pro Seller'),
    ('enterprise', 'Enterprise'),
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    unlimited_access = models.BooleanField(default=False)  # bypasses every limit below — for your own account

    def __str__(self):
        return self.business_name


class DismissedNotification(models.Model):
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='dismissed_notifications')
    notif_type = models.CharField(max_length=20)
    reference_id = models.PositiveIntegerField()
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('business', 'notif_type', 'reference_id')

    def __str__(self):
        return f"{self.notif_type} #{self.reference_id} dismissed by {self.business}"