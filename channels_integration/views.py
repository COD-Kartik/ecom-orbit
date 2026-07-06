from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, permissions
from .models import Channel, ProductListing
from .serializers import ChannelSerializer, ProductListingSerializer
from products.models import Product
from accounts.models import BusinessProfile

def get_user_business(user):
    try:
        return BusinessProfile.objects.get(user=user)
    except BusinessProfile.DoesNotExist:
        return None

# ── API ViewSets ──────────────────────────────────────────────────
class ChannelViewSet(viewsets.ModelViewSet):
    serializer_class = ChannelSerializer
    permission_classes = [permissions.AllowAny]
    def get_queryset(self):
        return Channel.objects.all()

class ProductListingViewSet(viewsets.ModelViewSet):
    serializer_class = ProductListingSerializer
    permission_classes = [permissions.AllowAny]
    def get_queryset(self):
        return ProductListing.objects.all()

# ── UI Views ──────────────────────────────────────────────────────
@login_required
def channel_list(request):
    business = get_user_business(request.user)
    channels = Channel.objects.filter(business=business).order_by('-created_at')

    if request.method == 'POST':
        Channel.objects.create(
            name=request.POST.get('name'),
            platform_type=request.POST.get('platform_type'),
            is_active=request.POST.get('is_active') == 'true',
            business=business,
        )
        return redirect('channel_list')

    return render(request, 'channels/channel_list.html', {
        'channels'        : channels,
        'total_channels'  : channels.count(),
        'active_channels' : channels.filter(is_active=True).count(),
        'platform_choices': Channel.PLATFORM_CHOICES,
        'business'        : business,
    })

@login_required
def channel_delete(request, pk):
    business = get_user_business(request.user)
    get_object_or_404(Channel, pk=pk, business=business).delete()
    return redirect('channel_list')

@login_required
def channel_toggle(request, pk):
    business = get_user_business(request.user)
    channel  = get_object_or_404(Channel, pk=pk, business=business)
    channel.is_active = not channel.is_active
    channel.save()
    return redirect('channel_list')

@login_required
def publish_product(request, product_id):
    business = get_user_business(request.user)
    product  = get_object_or_404(Product, pk=product_id, business=business)
    channels = Channel.objects.filter(business=business, is_active=True)

    if not channels.exists():
        return redirect('product_list')

    for channel in channels:
        listing, created = ProductListing.objects.get_or_create(
            product=product,
            channel=channel,
            defaults={'status': 'published'}
        )
        if not created and listing.status != 'published':
            listing.status = 'published'
            listing.save()

    return redirect('listing_list')

@login_required
def listing_list(request):
    business = get_user_business(request.user)
    channels = Channel.objects.filter(business=business)
    listings = ProductListing.objects.filter(
        channel__in=channels
    ).select_related('product', 'channel').order_by('-id')

    return render(request, 'channels/listing_list.html', {
        'listings'  : listings,
        'total'     : listings.count(),
        'published' : listings.filter(status='published').count(),
        'pending'   : listings.filter(status='pending').count(),
        'failed'    : listings.filter(status='failed').count(),
        'products'  : Product.objects.filter(business=business),
        'channels'  : channels.filter(is_active=True),
        'business'  : business,
    })

@login_required
def listing_status_update(request, pk):
    business = get_user_business(request.user)
    channels = Channel.objects.filter(business=business)
    listing  = get_object_or_404(ProductListing, pk=pk, channel__in=channels)
    new_status = request.POST.get('status')
    if new_status in ['pending', 'published', 'failed']:
        listing.status = new_status
        listing.save()
    return redirect('listing_list')

@login_required
def listing_delete(request, pk):
    business = get_user_business(request.user)
    channels = Channel.objects.filter(business=business)
    get_object_or_404(ProductListing, pk=pk, channel__in=channels).delete()
    return redirect('listing_list')