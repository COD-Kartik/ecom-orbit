from django.db import models
from accounts.models import BusinessProfile
from products.models import Product
from channels_integration.models import Channel
from django.utils import timezone

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    )
    business         = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    channel           = models.ForeignKey(Channel, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    customer_name     = models.CharField(max_length=150)
    customer_email    = models.EmailField(blank=True, null=True)
    customer_phone    = models.CharField(max_length=20, blank=True, null=True)
    shipping_address  = models.TextField(blank=True, null=True)
    total_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status    = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"


class OrderItem(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product    = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    quantity   = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.title if self.product else 'Deleted Product'}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price
    
class Discount(models.Model):
    TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    business          = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='discounts')
    code              = models.CharField(max_length=30)
    discount_type     = models.CharField(max_length=20, choices=TYPE_CHOICES, default='percentage')
    value             = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount  = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    usage_limit       = models.PositiveIntegerField(blank=True, null=True)
    times_used        = models.PositiveIntegerField(default=0)
    start_date        = models.DateField()
    expiry_date       = models.DateField()
    is_active         = models.BooleanField(default=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('business', 'code')

    def __str__(self):
        return f"{self.code} ({self.business.business_name})"

    @property
    def status(self):
        today = timezone.now().date()
        if not self.is_active:
            return 'inactive'
        if today < self.start_date:
            return 'scheduled'
        if today > self.expiry_date:
            return 'expired'
        return 'active'
    