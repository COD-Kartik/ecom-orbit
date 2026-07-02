from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import viewsets, permissions
from .models import Channel, ProductListing
from .serializers import ChannelSerializer, ProductListingSerializer

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
        name = request.POST.get('name')
        platform_type = request.POST.get('platform_type')
        is_active = request.POST.get('is_active') == 'true'
        Channel.objects.create(
            name=name,
            platform_type=platform_type,
            is_active=is_active,
        )
        return redirect('channel_list')

    return render(request, 'channels/channel_list.html', {
        'channels': channels,
        'total_channels': channels.count(),
        'active_channels': channels.filter(is_active=True).count(),
        'platform_choices': Channel.PLATFORM_CHOICES,
    })

def channel_delete(request, pk):
    channel = get_object_or_404(Channel, pk=pk)
    channel.delete()
    return redirect('channel_list')

def channel_toggle(request, pk):
    # Why? Sellers need to quickly enable/disable a channel
    # without deleting it — toggle flips is_active status
    channel = get_object_or_404(Channel, pk=pk)
    channel.is_active = not channel.is_active
    channel.save()
    return redirect('channel_list')