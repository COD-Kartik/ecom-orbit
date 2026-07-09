import json
import math
from datetime import timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.utils import timezone
from accounts.models import BusinessProfile
from orders.models import Order, OrderItem


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

    circumference = 2 * math.pi * 50
    status_order = ['delivered', 'shipped', 'processing', 'pending', 'cancelled']
    status_counts = {s: orders.filter(status=s).count() for s in status_order}

    donut_segments = []
    offset = 0
    for status in status_order:
        count = status_counts[status]
        length = (count / total_orders) * circumference if total_orders > 0 and count > 0 else 0
        donut_segments.append({
            'status': status,
            'count': count,
            'color': STATUS_COLORS[status],
            'dasharray': f"{length:.2f} {circumference:.2f}",
            'dashoffset': f"-{offset:.2f}",
        })
        offset += length

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

    top_products = (
        OrderItem.objects.filter(order__business=business)
        .values('product__title')
        .annotate(total_sold=Sum('quantity'), revenue=Sum(F('quantity') * F('unit_price')))
        .order_by('-revenue')[:6]
    )

    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day_totals = {i: 0 for i in range(7)}
    for order in orders.only('created_at', 'total_amount'):
        weekday = order.created_at.weekday()
        day_totals[weekday] += float(order.total_amount)

    max_day_value = max(day_totals.values()) if any(day_totals.values()) else 1
    day_chart = []
    for i, name in enumerate(day_names):
        value = day_totals[i]
        height_pct = round((value / max_day_value) * 100, 1) if max_day_value > 0 else 0
        day_chart.append({'label': name, 'value': value, 'height_pct': height_pct})

    today = timezone.now().date()
    date_range = [today - timedelta(days=i) for i in range(29, -1, -1)]
    daily_revenue = {d: 0 for d in date_range}
    daily_orders = {d: 0 for d in date_range}

    for order in orders.filter(created_at__date__gte=date_range[0]):
        order_date = order.created_at.date()
        if order_date in daily_revenue:
            daily_revenue[order_date] += float(order.total_amount)
            daily_orders[order_date] += 1

    trend_labels = [d.strftime('%b %d') for d in date_range]
    trend_revenue_data = [round(daily_revenue[d], 2) for d in date_range]
    trend_orders_data = [daily_orders[d] for d in date_range]

    channel_labels = [c['name'] for c in channel_data]
    channel_revenue_data = [float(c['revenue']) for c in channel_data]
    channel_orders_data = []
    for c in channel_data:
        if c['name'] == 'Manual':
            channel_orders_data.append(orders.filter(channel__isnull=True).count())
        else:
            channel_orders_data.append(orders.filter(channel__name=c['name']).count())

    chart_data = {
        'trend': {'labels': trend_labels, 'revenue': trend_revenue_data, 'orders': trend_orders_data},
        'channel': {'labels': channel_labels, 'revenue': channel_revenue_data, 'orders': channel_orders_data},
    }

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
        'chart_data_json': json.dumps(chart_data),
    })