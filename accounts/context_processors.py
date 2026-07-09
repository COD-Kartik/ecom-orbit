from django.utils import timezone
from accounts.models import BusinessProfile
from products.models import Product
from orders.models import Order


def notifications_context(request):
    if not request.user.is_authenticated:
        return {}

    try:
        business = BusinessProfile.objects.get(user=request.user)
    except BusinessProfile.DoesNotExist:
        return {'notif_count': 0, 'notif_preview': []}

    preview = []

    low_stock_products = Product.objects.filter(business=business, stock__lte=5).order_by('-created_at')[:3]
    for p in low_stock_products:
        preview.append({
            'type': 'low-stock',
            'text': f'{p.title} is running low ({p.stock} left)',
            'url': f'/dashboard/products/{p.id}/edit/',
            'created_at': p.created_at,
        })

    recent_orders = Order.objects.filter(business=business).order_by('-created_at')[:3]
    for o in recent_orders:
        preview.append({
            'type': 'new-order',
            'text': f'New order #ORD-{o.id} from {o.customer_name}',
            'url': f'/dashboard/orders/{o.id}/',
            'created_at': o.created_at,
        })

    # Bell badge count = items newer than last time the bell was opened
    last_viewed = business.notifications_last_viewed
    if last_viewed:
        unread_count = sum(1 for n in preview if n['created_at'] > last_viewed)
    else:
        unread_count = len(preview)

    return {
        'notif_count': unread_count,
        'notif_preview': sorted(preview, key=lambda x: x['created_at'], reverse=True)[:5],
    }