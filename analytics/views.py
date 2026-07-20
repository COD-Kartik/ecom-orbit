import json
from datetime import timedelta
from collections import defaultdict
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.utils import timezone
from django.db.models.functions import ExtractWeekDay
from accounts.models import BusinessProfile
from orders.models import Order, OrderItem
from channels_integration.models import Channel

def get_user_business(user):
    try:
        return BusinessProfile.objects.get(user=user)
    except BusinessProfile.DoesNotExist:
        return None

def compute_trend(current, prior):
    current = float(current)
    prior = float(prior)
    if prior > 0:
        diff = ((current - prior) / prior) * 100
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff:.1f}% vs prior period", diff >= 0
    return "No prior data", True

@login_required
def analytics_view(request):
    business = get_user_business(request.user)
    orders = Order.objects.filter(business=business) if business else Order.objects.none()

    # 1. Parse date filter parameter
    today = timezone.now().date()
    date_range = request.GET.get('date_range', '30')
    date_from_str = request.GET.get('date_from', '')
    date_to_str = request.GET.get('date_to', '')

    if date_range == '7':
        start_date = today - timedelta(days=6)
        end_date = today
        date_label = "Last 7 days"
    elif date_range == '90':
        start_date = today - timedelta(days=89)
        end_date = today
        date_label = "Last 90 days"
    elif date_range == 'custom':
        try:
            start_date = timezone.datetime.strptime(date_from_str, '%Y-%m-%d').date() if date_from_str else (today - timedelta(days=29))
        except ValueError:
            start_date = today - timedelta(days=29)
        try:
            end_date = timezone.datetime.strptime(date_to_str, '%Y-%m-%d').date() if date_to_str else today
        except ValueError:
            end_date = today
        date_label = "Custom range"
    else:
        date_range = '30'
        start_date = today - timedelta(days=29)
        end_date = today
        date_label = "Last 30 days"

    # 2. Determine prior period bounds for trend comparison
    delta = (end_date - start_date).days + 1
    prior_end_date = start_date - timedelta(days=1)
    prior_start_date = prior_end_date - timedelta(days=delta - 1)

    # 3. Filter orders querysets
    orders_current = orders.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    orders_prior = orders.filter(created_at__date__gte=prior_start_date, created_at__date__lte=prior_end_date)

    # 4. Compute KPIs
    rev_current = orders_current.aggregate(total=Sum('total_amount'))['total'] or 0
    rev_prior = orders_prior.aggregate(total=Sum('total_amount'))['total'] or 0
    revenue_trend_str, revenue_trend_up = compute_trend(rev_current, rev_prior)

    ord_current = orders_current.count()
    ord_prior = orders_prior.count()
    orders_trend_str, orders_trend_up = compute_trend(ord_current, ord_prior)

    aov_current = float(rev_current) / ord_current if ord_current > 0 else 0.0
    aov_prior = float(rev_prior) / ord_prior if ord_prior > 0 else 0.0
    aov_trend_str, aov_trend_up = compute_trend(aov_current, aov_prior)

    cust_current = orders_current.exclude(customer_email__isnull=True).exclude(customer_email='').values('customer_email').distinct().count()
    cust_prior = orders_prior.exclude(customer_email__isnull=True).exclude(customer_email='').values('customer_email').distinct().count()
    customers_trend_str, customers_trend_up = compute_trend(cust_current, cust_prior)

    # 5. Sales Performance Trend array (Daily spacing)
    daily_data = {}
    curr = start_date
    while curr <= end_date:
        daily_data[curr] = {'revenue': 0.0, 'orders': 0}
        curr += timedelta(days=1)

    for order in orders_current:
        odate = order.created_at.date()
        if odate in daily_data:
            daily_data[odate]['revenue'] += float(order.total_amount)
            daily_data[odate]['orders'] += 1

    daily_points = []
    for d in sorted(daily_data.keys()):
        daily_points.append({
            'date': d.strftime('%Y-%m-%d'),
            'label': d.strftime('%b %d'),
            'revenue': round(daily_data[d]['revenue'], 2),
            'orders': daily_data[d]['orders']
        })

    # 6. Revenue by Channel
    channels_qs = Channel.objects.filter(business=business) if business else Channel.objects.none()
    channels_dict = {c.id: c for c in channels_qs}

    color_map = {
        'facebook': '#1877f2',
        'instagram': '#e1306c',
        'whatsapp': '#25D366',
        'flipkart': '#2874F0',
        'twitter': '#0f172a',
        'linkedin': '#0A66C2',
        'pinterest': '#E60023',
        'youtube': '#FF0000',
        'other': '#7c3aed',
    }

    channel_revs = orders_current.values('channel_id').annotate(revenue=Sum('total_amount'), count=Count('id')).order_by('-revenue')
    channel_data = []
    total_rev_float = float(rev_current)

    for item in channel_revs:
        ch_id = item['channel_id']
        rev = float(item['revenue'] or 0.0)
        count = item['count']
        pct = round((rev / total_rev_float * 100), 1) if total_rev_float > 0 else 0.0

        if ch_id is None:
            name = "Manual"
            color = "#64748b"
        else:
            ch = channels_dict.get(ch_id)
            name = ch.name if ch else f"Channel #{ch_id}"
            platform = ch.platform_type.lower().strip() if ch else 'other'
            color = color_map.get(platform, '#6366f1')

        channel_data.append({
            'name': name,
            'revenue': round(rev, 2),
            'count': count,
            'percent': pct,
            'color': color
        })

    # 7. Fulfillment Status Distribution
    status_choices = ['delivered', 'shipped', 'processing', 'pending', 'cancelled']
    status_counts = {s: orders_current.filter(status=s).count() for s in status_choices}
    status_colors = {
        'delivered': '#10b981',
        'shipped': '#3b82f6',
        'processing': '#4f46e5',
        'pending': '#f59e0b',
        'cancelled': '#ef4444',
    }

    status_data = []
    for s in status_choices:
        count = status_counts[s]
        pct = round((count / ord_current) * 100, 1) if ord_current > 0 else 0.0
        status_data.append({
            'status': s.capitalize(),
            'count': count,
            'percent': pct,
            'color': status_colors[s]
        })

    # 8. Top Performing Products Grouping
    product_sales = defaultdict(lambda: {'sold': 0, 'revenue': 0.0, 'product': None})
    for item in OrderItem.objects.filter(order__in=orders_current).select_related('product'):
        if item.product:
            key = item.product.id
            product_sales[key]['sold'] += item.quantity
            product_sales[key]['revenue'] += float(item.quantity * item.unit_price)
            product_sales[key]['product'] = item.product

    top_products_data = sorted(product_sales.values(), key=lambda x: x['revenue'], reverse=True)[:5]
    top_revenue = top_products_data[0]['revenue'] if top_products_data else 1.0

    for p in top_products_data:
        p['percent'] = round((p['revenue'] / top_revenue) * 100, 1) if top_revenue > 0 else 0.0

    # 9. Sales by Day of Week
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day_revenue = [0.0] * 7
    day_orders = [0] * 7

    try:
        weekday_data = (
            orders_current
            .annotate(weekday=ExtractWeekDay('created_at'))
            .values('weekday')
            .annotate(revenue=Sum('total_amount'), count=Count('id'))
        )
        django_weekday_map = {
            2: 0, # Mon
            3: 1, # Tue
            4: 2, # Wed
            5: 3, # Thu
            6: 4, # Fri
            7: 5, # Sat
            1: 6, # Sun
        }
        for item in weekday_data:
            wd = item['weekday']
            if wd is not None:
                wd_int = int(wd)
                if wd_int in django_weekday_map:
                    idx = django_weekday_map[wd_int]
                    day_revenue[idx] = float(item['revenue'] or 0.0)
                    day_orders[idx] = item['count']
    except Exception:
        # Fallback to local python loop
        for o in orders_current:
            w = o.created_at.weekday()
            day_revenue[w] += float(o.total_amount)
            day_orders[w] += 1

    # 10. Package data feeds for Chart.js
    chart_data = {
        'daily': daily_points,
        'weekday': {
            'labels': day_names,
            'revenue': day_revenue,
            'orders': day_orders,
        },
        'status': {
            'labels': [s['status'] for s in status_data],
            'data': [s['count'] for s in status_data],
            'colors': [s['color'] for s in status_data],
            'percents': [s['percent'] for s in status_data],
        }
    }

    return render(request, 'analytics/analytics.html', {
        'business': business,
        'total_orders': ord_current,
        'total_revenue': round(rev_current, 2),
        'avg_order_value': round(aov_current, 2),
        'total_customers': cust_current,
        
        # Trend indicators
        'revenue_trend_str': revenue_trend_str,
        'revenue_trend_up': revenue_trend_up,
        'orders_trend_str': orders_trend_str,
        'orders_trend_up': orders_trend_up,
        'aov_trend_str': aov_trend_str,
        'aov_trend_up': aov_trend_up,
        'customers_trend_str': customers_trend_str,
        'customers_trend_up': customers_trend_up,

        # Detailed Breakdowns
        'channel_data': channel_data,
        'status_data': status_data,
        'top_products': top_products_data,
        
        # State tracking
        'has_orders': ord_current > 0,
        'date_range': date_range,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'date_label': date_label,
        'reporting_range': f"{start_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')}",
        'chart_data_json': json.dumps(chart_data),
    })