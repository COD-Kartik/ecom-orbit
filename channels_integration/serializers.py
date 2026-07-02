from rest_framework import serializers
from .models import Channel, ProductListing

class ChannelSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(
        source='get_platform_type_display', read_only=True
    )

    class Meta:
        model = Channel
        fields = [
            'id', 'name', 'platform_type', 'platform_display',
            'is_active', 'created_at'
        ]

class ProductListingSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ProductListing
        fields = [
            'id', 'product', 'product_title', 'channel',
            'channel_name', 'external_id', 'status',
            'status_display', 'published_at'
        ]