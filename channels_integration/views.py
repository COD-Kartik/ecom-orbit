from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, permissions
from .models import Channel, ProductListing
from .serializers import ChannelSerializer, ProductListingSerializer
from products.models import Product
from accounts.models import BusinessProfile
from django.contrib import messages

def get_user_business(user):
    try:
        return BusinessProfile.objects.get(user=user)
    except BusinessProfile.DoesNotExist:
        return None

# ── API ViewSets ──────────────────────────────────────────────────
class ChannelViewSet(viewsets.ModelViewSet):
    serializer_class = ChannelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Channel.objects.filter(business=business) if business else Channel.objects.none()

    def perform_create(self, serializer):
        business = get_user_business(self.request.user)
        serializer.save(business=business)


class ProductListingViewSet(viewsets.ModelViewSet):
    serializer_class = ProductListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        channels = Channel.objects.filter(business=business) if business else Channel.objects.none()
        return ProductListing.objects.filter(channel__in=channels)

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
    channel = get_object_or_404(Channel, pk=pk, business=business)
    channel.is_active = not channel.is_active
    channel.save()

    if not channel.is_active:
        # Channel turned off — its listings can no longer be considered "published"
        ProductListing.objects.filter(channel=channel, status='published').update(status='pending')
        messages.info(request, f'"{channel.name}" deactivated. Its listings are now marked pending.')
    else:
        messages.success(request, f'"{channel.name}" reactivated.')

    return redirect('channel_list')

@login_required
def select_channels_to_publish(request, product_id):
    business = get_user_business(request.user)
    product = get_object_or_404(Product, pk=product_id, business=business)
    channels = Channel.objects.filter(business=business, is_active=True)

    if not channels.exists():
        messages.error(request, 'No active channels connected. Please connect a channel first.')
        return redirect('channel_list')

    if request.method == 'POST':
        selected_ids = request.POST.getlist('channel_ids')
        if not selected_ids:
            messages.error(request, 'Please select at least one channel.')
            return redirect('select_channels_to_publish', product_id=product.id)

        selected_channels = channels.filter(id__in=selected_ids)
        for channel in selected_channels:
            listing, created = ProductListing.objects.get_or_create(
                product=product,
                channel=channel,
                defaults={'status': 'published'}
            )
            if not created and listing.status != 'published':
                listing.status = 'published'
                listing.save()

        # Unpublish from channels that were unchecked but previously published
        unselected_channels = channels.exclude(id__in=selected_ids)
        ProductListing.objects.filter(product=product, channel__in=unselected_channels, status='published').update(status='pending')

        messages.success(request, f'"{product.title}" updated across {selected_channels.count()} channel(s).')
        return redirect('listing_list')

    # GET — show checkboxes with current publish status per channel
    published_channel_ids = set(
        ProductListing.objects.filter(product=product, status='published').values_list('channel_id', flat=True)
    )

    return render(request, 'channels/select_channels.html', {
        'product': product,
        'channels': channels,
        'published_channel_ids': published_channel_ids,
    })


@login_required
def publish_product(request, product_id):
    """Quick Publish — publishes to ALL active channels at once."""
    business = get_user_business(request.user)
    product = get_object_or_404(Product, pk=product_id, business=business)
    channels = Channel.objects.filter(business=business, is_active=True)

    if not channels.exists():
        messages.error(request, 'No active channels connected. Please connect a channel first before publishing.')
        return redirect('channel_list')

    for channel in channels:
        listing, created = ProductListing.objects.get_or_create(
            product=product,
            channel=channel,
            defaults={'status': 'published'}
        )
        if not created and listing.status != 'published':
            listing.status = 'published'
            listing.save()

    messages.success(request, f'"{product.title}" published to {channels.count()} channel(s).')
    return redirect('listing_list')
@login_required
def listing_list(request):
    business = get_user_business(request.user)
    channels = Channel.objects.filter(business=business)
    listings = ProductListing.objects.filter(channel__in=channels).select_related('product', 'channel')

    selected_channel_id = request.GET.get('channel')
    if selected_channel_id:
        listings = listings.filter(channel_id=selected_channel_id)

    listings = listings.order_by('-id')  # most recently added/updated first

    return render(request, 'channels/listing_list.html', {
        'listings': listings,
        'total': ProductListing.objects.filter(channel__in=channels).count(),
        'published': ProductListing.objects.filter(channel__in=channels, status='published').count(),
        'pending': ProductListing.objects.filter(channel__in=channels, status='pending').count(),
        'failed': ProductListing.objects.filter(channel__in=channels, status='failed').count(),
        'products': Product.objects.filter(business=business),
        'channels': channels.filter(is_active=True),
        'all_channels': channels,
        'selected_channel_id': int(selected_channel_id) if selected_channel_id else None,
        'business': business,
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