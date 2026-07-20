from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, permissions

from channels_integration.whatsapp_client import check_whatsapp_connection
from .models import Channel, ProductListing, SyncLog
from .serializers import ChannelSerializer, ProductListingSerializer
from products.models import Product
from accounts.models import BusinessProfile
from django.contrib import messages
from django.utils import timezone
from .flipkart_client import get_flipkart_access_token
from .flipkart_client import get_flipkart_access_token, push_product_to_flipkart, fetch_flipkart_orders
from orders.models import Order, OrderItem

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
import json
from django.conf import settings
from .models import Channel, ProductListing, SyncLog, WebhookLog

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

    # Get healthy channels count (connected + active)
    healthy_channels = channels.filter(is_active=True, connection_status='connected').count()
    
    # Get pending synchronizations count (listings that are pending)
    pending_syncs = ProductListing.objects.filter(channel__in=channels, status='pending').count()
    
    # Get synced products count (listings that are published)
    synced_today = ProductListing.objects.filter(channel__in=channels, status='published').count()

    # Get recent sync logs
    sync_logs = SyncLog.objects.filter(channel__in=channels).order_by('-created_at')[:5]

    attention_needed = channels.filter(connection_status='error').count()

    return render(request, 'channels/channel_list.html', {
        'channels'          : channels,
        'total_channels'    : channels.count(),
        'active_channels'   : channels.filter(is_active=True).count(),
        'inactive_channels' : channels.filter(is_active=False).count(),
        'healthy_channels'  : healthy_channels,
        'attention_needed'  : attention_needed,
        'pending_syncs'     : pending_syncs,
        'synced_today'      : synced_today,
        'sync_logs'         : sync_logs,
        'platform_choices'  : Channel.PLATFORM_CHOICES,
        'business'          : business,
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

    # Compute coverage variables
    coverage_active = channels.filter(is_active=True).count()
    coverage_total = channels.count()
    
    # Compute successful syncs today (published status count)
    successful_syncs_today = listings.filter(status='published').count()

    # Get recent sync logs
    sync_logs = SyncLog.objects.filter(channel__in=channels).order_by('-created_at')[:5]

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
        'coverage_active': coverage_active,
        'coverage_total': coverage_total,
        'successful_syncs_today': successful_syncs_today,
        'sync_logs': sync_logs,
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


#
@login_required
def test_flipkart_connection(request, pk):
    business = get_user_business(request.user)
    channel = get_object_or_404(Channel, pk=pk, business=business)

    result = get_flipkart_access_token()
    channel.last_sync_attempt = timezone.now()

    if result['success']:
        channel.connection_status = 'connected'
        channel.last_sync_error = None
        messages.success(request, f'"{channel.name}" connected successfully to Flipkart.')
    else:
        channel.connection_status = 'error'
        channel.last_sync_error = f"HTTP {result.get('status_code')}: {result.get('error')}"
        messages.error(request, f'Connection to "{channel.name}" failed. See error details below.')

    channel.save()
    return redirect('channel_list')

@login_required
def sync_flipkart_now(request, pk):
    business = get_user_business(request.user)
    channel = get_object_or_404(Channel, pk=pk, business=business)

    token_result = get_flipkart_access_token()

    if not token_result['success']:
        channel.connection_status = 'error'
        channel.last_sync_error = f"Token request failed: HTTP {token_result.get('status_code')}: {token_result.get('error')}"
        channel.last_sync_attempt = timezone.now()
        channel.save()
        messages.error(request, f'Sync failed — could not authenticate with Flipkart. See channel status for details.')
        return redirect('channel_list')

    access_token = token_result['access_token']
    channel.connection_status = 'connected'
    channel.last_sync_attempt = timezone.now()
    channel.save()

    from products.models import Product
    products = Product.objects.filter(business=business, is_active=True)

    synced_count = 0
    failed_count = 0
    for product in products:
        result = push_product_to_flipkart(access_token, product)
        if result['success']:
            listing, created = ProductListing.objects.get_or_create(
                product=product,
                channel=channel,
                defaults={'status': 'published', 'external_id': result['sku_id']}
            )
            if not created:
                listing.status = 'published'
                listing.external_id = result['sku_id']
                listing.save()
            synced_count += 1
        else:
            failed_count += 1

    if synced_count > 0:
        messages.success(request, f'Sync complete: {synced_count} product(s) pushed to Flipkart.')
    if failed_count > 0:
        messages.warning(request, f'{failed_count} product(s) failed to sync — Flipkart API may be temporarily unavailable.')
    if synced_count == 0 and failed_count == 0:
        messages.info(request, 'No active products to sync.')

    return redirect('listing_list')

@login_required
def sync_flipkart_orders(request, pk):
    business = get_user_business(request.user)
    channel = get_object_or_404(Channel, pk=pk, business=business)

    token_result = get_flipkart_access_token()
    if not token_result['success']:
        channel.connection_status = 'error'
        channel.last_sync_error = f"Token request failed: {token_result.get('error')}"
        channel.last_sync_attempt = timezone.now()
        channel.save()
        SyncLog.objects.create(channel=channel, action='order_import', success_count=0, failed_count=0, status='failed')
        messages.error(request, 'Could not authenticate with Flipkart to fetch orders.')
        return redirect('channel_list')

    access_token = token_result['access_token']
    order_result = fetch_flipkart_orders(access_token)
    channel.last_sync_attempt = timezone.now()

    if not order_result['success']:
        channel.connection_status = 'error'
        channel.last_sync_error = f"Order fetch failed: HTTP {order_result.get('status_code')}: {order_result.get('error')}"
        channel.save()
        SyncLog.objects.create(channel=channel, action='order_import', success_count=0, failed_count=0, status='failed')
        messages.error(request, 'Failed to fetch orders from Flipkart. See channel status for details.')
        return redirect('channel_list')

    channel.connection_status = 'connected'
    channel.save()

    raw_data = order_result.get('data', {})
    order_items = raw_data.get('orderItems', []) or raw_data.get('orders', [])

    created_count = 0
    skipped_count = 0

    for item in order_items:
        try:
            external_order_id = item.get('orderItemId') or item.get('orderId')
            if not external_order_id:
                skipped_count += 1
                continue

            if Order.objects.filter(business=business, channel=channel, id=external_order_id).exists():
                skipped_count += 1
                continue

            buyer_info = item.get('buyerDetails', {}) or item.get('customer', {})
            customer_name = buyer_info.get('fullName', 'Flipkart Customer')

            Order.objects.create(
                business=business,
                channel=channel,
                customer_name=customer_name,
                customer_email='',
                customer_phone=buyer_info.get('phone', ''),
                shipping_address=str(item.get('deliveryAddress', '')),
                total_amount=item.get('priceComponents', {}).get('sellingPrice', 0),
                status='pending',
            )
            created_count += 1
        except Exception:
            skipped_count += 1
            continue

    log_status = 'success' if created_count > 0 else 'success'  # no items to import isn't a failure
    SyncLog.objects.create(channel=channel, action='order_import', success_count=created_count, failed_count=skipped_count, status=log_status)

    if created_count > 0:
        messages.success(request, f'{created_count} new order(s) imported from Flipkart.')
    else:
        messages.info(request, f'No new orders to import. ({skipped_count} skipped/already existing)')

    return redirect('order_list')


@login_required
def test_whatsapp_connection(request, pk):
    business = get_user_business(request.user)
    channel = get_object_or_404(Channel, pk=pk, business=business)

    result = check_whatsapp_connection()
    channel.last_sync_attempt = timezone.now()

    if result['success']:
        channel.connection_status = 'connected'
        channel.last_sync_error = None
        messages.success(request, f'"{channel.name}" connected successfully to WhatsApp ({result.get("display_phone_number")}).')
    else:
        channel.connection_status = 'error'
        channel.last_sync_error = f"HTTP {result.get('status_code')}: {result.get('error')}"
        messages.error(request, f'Connection to "{channel.name}" failed. See error details below.')

    channel.save()
    return redirect('channel_list')

@csrf_exempt
def whatsapp_webhook(request):
    """
    Meta calls this endpoint directly — not a logged-in user, so no
    @login_required and no CSRF (Meta doesn't send Django's CSRF token).

    GET: one-time verification handshake Meta performs when you register
    this URL in the dashboard.
    POST: real incoming events (messages, orders) once verified.
    """
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            return HttpResponse(challenge)
        else:
            return HttpResponse('Verification failed', status=403)

    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        print("=== WHATSAPP WEBHOOK RECEIVED ===")
        print(json.dumps(payload, indent=2))
        print("==================================")

        # Real persisted log — every webhook call gets saved, regardless
        # of whether it turns into an order, so nothing is lost once the
        # terminal scrolls past it.
        whatsapp_channel = Channel.objects.filter(platform_type='whatsapp').first()
        event_type = 'unknown'
        try:
            entries = payload.get('entry', [])
            for entry in entries:
                for change in entry.get('changes', []):
                    event_type = change.get('field', 'unknown')
        except Exception:
            pass

        WebhookLog.objects.create(
            channel=whatsapp_channel,
            event_type=event_type,
            raw_payload=payload,
        )

        try:
            entries = payload.get('entry', [])
            for entry in entries:
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    contacts = value.get('contacts', [])

                    contact_name = contacts[0]['profile']['name'] if contacts else 'WhatsApp Customer'

                    for message in messages:
                        if message.get('type') != 'order':
                            print(f"Skipped non-order message type: {message.get('type')}")
                            continue

                        customer_phone = message.get('from', '')
                        order_data = message.get('order', {})
                        product_items = order_data.get('product_items', [])
                        buyer_note = order_data.get('text', '')

                        if not product_items:
                            print("Order message had no product_items — skipping.")
                            continue

                        channel = Channel.objects.filter(platform_type='whatsapp').first()
                        if not channel:
                            print("No WhatsApp channel found — cannot attach order.")
                            continue

                        business = channel.business

                        total_amount = 0
                        line_items_to_create = []

                        for item in product_items:
                            retailer_id = item.get('product_retailer_id', '')
                            quantity = int(item.get('quantity', 1))
                            item_price = float(item.get('item_price', 0))

                            product = None
                            if retailer_id.startswith('ECOMORBIT-'):
                                try:
                                    product_id = int(retailer_id.replace('ECOMORBIT-', ''))
                                    product = Product.objects.filter(id=product_id, business=business).first()
                                except ValueError:
                                    product = None

                            total_amount += item_price * quantity
                            line_items_to_create.append({
                                'product': product,
                                'quantity': quantity,
                                'unit_price': item_price,
                            })

                        order = Order.objects.create(
                            business=business,
                            channel=channel,
                            customer_name=contact_name,
                            customer_phone=customer_phone,
                            total_amount=total_amount,
                            status='pending',
                            payment_status='unpaid',
                            internal_notes=f"WhatsApp order. Buyer note: {buyer_note}" if buyer_note else "Received via WhatsApp.",
                        )

                        for line_item in line_items_to_create:
                            OrderItem.objects.create(
                                order=order,
                                product=line_item['product'],
                                quantity=line_item['quantity'],
                                unit_price=line_item['unit_price'],
                            )

                        SyncLog.objects.create(
                            channel=channel,
                            action='order_import',
                            success_count=1,
                            failed_count=0,
                            status='success',
                        )

                        print(f"Created Order #{order.id} for {contact_name} — {len(line_items_to_create)} item(s), total {total_amount}")

        except Exception as e:
            print(f"Error processing WhatsApp webhook: {e}")

        return JsonResponse({'status': 'received'}, status=200)

    return HttpResponse(status=405)

@login_required
def webhook_logs_view(request):
    business = get_user_business(request.user)
    logs = WebhookLog.objects.filter(channel__business=business).order_by('-received_at') if business else WebhookLog.objects.none()

    from django.core.paginator import Paginator
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'channels/webhook_logs.html', {
        'page_obj': page_obj,
        'total_logs': logs.count(),
        'business': business,
    })

def _summarize_webhook_payload(payload):
    """Turn a raw webhook payload into a short, human-readable summary for the toast."""
    try:
        entries = payload.get('entry', [])
        for entry in entries:
            for change in entry.get('changes', []):
                value = change.get('value', {})
                messages_list = value.get('messages', [])
                contacts = value.get('contacts', [])
                contact_name = contacts[0]['profile']['name'] if contacts else 'a customer'
                for message in messages_list:
                    if message.get('type') == 'order':
                        order_data = message.get('order', {})
                        item_count = len(order_data.get('product_items', []))
                        return f"New order from {contact_name} — {item_count} item(s)"
                    elif message.get('type') == 'text':
                        body = message.get('text', {}).get('body', '')
                        return f"Message from {contact_name}: \"{body[:60]}\""
        return "New WhatsApp webhook event received"
    except Exception:
        return "New WhatsApp webhook event received"


@login_required
def api_latest_webhook_logs(request):
    business = get_user_business(request.user)
    since_id = int(request.GET.get('since_id', 0))

    logs = WebhookLog.objects.filter(
        channel__business=business,
        id__gt=since_id
    ).order_by('id') if business else WebhookLog.objects.none()

    results = []
    latest_id = since_id
    for log in logs:
        results.append({
            'id': log.id,
            'event_type': log.event_type,
            'received_at': log.received_at.strftime('%H:%M:%S'),
            'summary': _summarize_webhook_payload(log.raw_payload),
            'raw_payload': log.raw_payload,
        })
        latest_id = log.id

    return JsonResponse({'logs': results, 'latest_id': latest_id})