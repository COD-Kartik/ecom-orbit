from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from accounts.models import BusinessProfile
from orders.models import Order, OrderItem
import math


def get_user_business(user):
    try:
        return BusinessProfile.objects.get(user=user)
    except BusinessProfile.DoesNotExist:
        return None


STATUS_COLORS = {
    'delivered': '#10b981',
    'shipped': '#3b82f6',
    'processing': '#4f46e5',
    'pending': '#f59e0b',
    'cancelled': '#ef4444',
}


@login_required
def analytics_view(request):
    business = get_user_business(request.user)
    orders = Order.objects.filter(business=business) if business else Order.objects.none()

    total_orders = orders.count()
    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0
    total_customers = (
        orders.values('customer_email')
        .exclude(customer_email__isnull=True)
        .exclude(customer_email='')
        .distinct()
        .count()
    )

    # ── Fulfillment status donut segments ──
    circumference = 2 * math.pi * 50  # r=50
    status_order = ['delivered', 'shipped', 'processing', 'pending', 'cancelled']
    status_counts = {s: orders.filter(status=s).count() for s in status_order}

    donut_segments = []
    offset = 0
    for status in status_order:
        count = status_counts[status]
        if total_orders > 0 and count > 0:
            length = (count / total_orders) * circumference
        else:
            length = 0
        donut_segments.append({
            'status': status,
            'count': count,
            'color': STATUS_COLORS[status],
            'dasharray': f"{length:.2f} {circumference:.2f}",
            'dashoffset': f"-{offset:.2f}",
        })
        offset += length

    # ── Revenue by channel ──
    channel_revenue = (
        orders.values('channel__name')
        .annotate(revenue=Sum('total_amount'), count=Count('id'))
        .order_by('-revenue')
    )
    channel_data = []
    if total_revenue > 0:
        for c in channel_revenue:
            pct = round((c['revenue'] or 0) / total_revenue * 100, 1)
            channel_data.append({
                'name': c['channel__name'] or 'Manual',
                'revenue': c['revenue'] or 0,
                'percent': pct,
            })

    # ── Top performing products ──
    top_products = (
        OrderItem.objects.filter(order__business=business)
        .values('product__title')
        .annotate(
            total_sold=Sum('quantity'),
            revenue=Sum(F('quantity') * F('unit_price'))
        )
        .order_by('-revenue')[:6]
    )

    # ── Sales by day of week ──
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day_totals = {i: 0 for i in range(7)}
    for order in orders.only('created_at', 'total_amount'):
        weekday = order.created_at.weekday()  # Mon=0 ... Sun=6
        day_totals[weekday] += float(order.total_amount)

    max_day_value = max(day_totals.values()) if any(day_totals.values()) else 1
    day_chart = []
    for i, name in enumerate(day_names):
        value = day_totals[i]
        height_pct = round((value / max_day_value) * 100, 1) if max_day_value > 0 else 0
        day_chart.append({'label': name, 'value': value, 'height_pct': height_pct})

    return render(request, 'analytics/analytics.html', {
        'business': business,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        'total_customers': total_customers,
        'donut_segments': donut_segments,
        'status_counts': status_counts,
        'channel_data': channel_data,
        'top_products': top_products,
        'day_chart': day_chart,
        'has_orders': total_orders > 0,
    })