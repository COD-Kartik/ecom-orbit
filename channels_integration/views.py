from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from rest_framework import viewsets, permissions
from .models import Channel, ProductListing
from .serializers import ChannelSerializer, ProductListingSerializer
from products.models import Product

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
def channel_list(request):
    channels = Channel.objects.all().order_by('-created_at')
    if request.method == 'POST':
        Channel.objects.create(
            name=request.POST.get('name'),
            platform_type=request.POST.get('platform_type'),
            is_active=request.POST.get('is_active') == 'true',
        )
        return redirect('channel_list')
    return render(request, 'channels/channel_list.html', {
        'channels': channels,
        'total_channels': channels.count(),
        'active_channels': channels.filter(is_active=True).count(),
        'platform_choices': Channel.PLATFORM_CHOICES,
    })

def channel_delete(request, pk):
    get_object_or_404(Channel, pk=pk).delete()
    return redirect('channel_list')

def channel_toggle(request, pk):
    channel = get_object_or_404(Channel, pk=pk)
    channel.is_active = not channel.is_active
    channel.save()
    return redirect('channel_list')

def publish_product(request, product_id):
    # Why? This is the core publishing logic —
    # creates a ProductListing for every active channel
    product = get_object_or_404(Product, pk=product_id)
    channels = Channel.objects.filter(is_active=True)

    if not channels.exists():
        return redirect('product_list')

    for channel in channels:
        # Only create if not already listed on this channel
        listing, created = ProductListing.objects.get_or_create(
            product=product,
            channel=channel,
            defaults={'status': 'published'}
        )
        if not created and listing.status != 'published':
            listing.status = 'published'
            listing.save()

    return redirect('listing_list')

def listing_list(request):
    listings = ProductListing.objects.all().select_related(
        'product', 'channel'
    ).order_by('-id')
    return render(request, 'channels/listing_list.html', {
        'listings': listings,
        'total': listings.count(),
        'published': listings.filter(status='published').count(),
        'pending': listings.filter(status='pending').count(),
        'failed': listings.filter(status='failed').count(),
        'products': Product.objects.all(),
        'channels': Channel.objects.filter(is_active=True),
    })

def listing_status_update(request, pk):
    # Why? Allows manual status update of a listing
    listing = get_object_or_404(ProductListing, pk=pk)
    new_status = request.POST.get('status')
    if new_status in ['pending', 'published', 'failed']:
        listing.status = new_status
        listing.save()
    return redirect('listing_list')

def listing_delete(request, pk):
    get_object_or_404(ProductListing, pk=pk).delete()
    return redirect('listing_list')