import csv 
from django.db.models import Count, Sum, Max
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from .models import Order, OrderItem
from .serializers import OrderSerializer
from accounts.models import BusinessProfile
import json
from django.utils import timezone
from products.models import Product
from datetime import datetime
from django.contrib import messages
from .models import Discount, Note
from django.core.paginator import Paginator
from django.db.models import Q
from products.models import Product, Category
from django.db.models import Count
from channels_integration.models import Channel, SyncLog
from django.db.models.functions import ExtractWeekDay


def get_user_business(user):
    try:
        return BusinessProfile.objects.get(user=user)
    except BusinessProfile.DoesNotExist:
        return None

# ── API ViewSet ───────────────────────────────────────────────────
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Order.objects.filter(business=business) if business else Order.objects.none()

    def perform_create(self, serializer):
        business = get_user_business(self.request.user)
        serializer.save(business=business)
# ── UI Views ──────────────────────────────────────────────────────
@login_required
def order_list(request):
    business = get_user_business(request.user)
    orders = Order.objects.filter(business=business).order_by('-created_at') if business else Order.objects.none()

    status_filter = request.GET.get('status')
    search_query = request.GET.get('q')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    stats_base = Order.objects.filter(business=business) if business else Order.objects.none()

    if status_filter:
        orders = orders.filter(status=status_filter)
    if search_query:
        cleaned_id = search_query.upper().replace('ORD-', '').replace('#', '').strip()
        q_filter = Q(customer_name__icontains=search_query)
        if cleaned_id.isdigit():
            q_filter |= Q(id=int(cleaned_id))
        orders = orders.filter(q_filter)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    products = Product.objects.filter(business=business) if business else Product.objects.none()

    # Channel Distribution — real order counts grouped by channel
    channel_distribution = (
        stats_base.values('channel__name')
        .annotate(order_count=Count('id'))
        .order_by('-order_count')
    )
    channel_distribution_data = [
        {'name': c['channel__name'] or 'Manual', 'count': c['order_count']}
        for c in channel_distribution
    ]

    # Real Flipkart channels for Marketplace Operations widget
    flipkart_channels = Channel.objects.filter(business=business, platform_type='flipkart') if business else Channel.objects.none()

    # Recent sync/import activity — real log, not fabricated
    recent_sync_logs = SyncLog.objects.filter(channel__business=business).select_related('channel')[:8] if business else SyncLog.objects.none()

    return render(request, 'orders/order_list.html', {
        'orders': page_obj,
        'page_obj': page_obj,
        'products': products,
        'total_orders': stats_base.count(),
        'pending_count': stats_base.filter(status='pending').count(),
        'processing_count': stats_base.filter(status='processing').count(),
        'shipped_count': stats_base.filter(status='shipped').count(),
        'delivered_count': stats_base.filter(status='delivered').count(),
        'cancelled_count': stats_base.filter(status='cancelled').count(),
        'current_status': status_filter or '',
        'search_query': search_query or '',
        'date_from': date_from or '',
        'date_to': date_to or '',
        'business': business,
        'channel_distribution': channel_distribution_data,
        'flipkart_channels': flipkart_channels,
        'recent_sync_logs': recent_sync_logs,
    })
@login_required
def order_detail(request, pk):
    business = get_user_business(request.user)
    order = get_object_or_404(Order, pk=pk, business=business)

    # Build a simple timeline from real order data — no separate activity log table needed
    status_order = ['pending', 'processing', 'shipped', 'delivered']
    timeline = [{'label': 'Order Placed', 'timestamp': order.created_at, 'done': True}]

    if order.status == 'cancelled':
        timeline.append({'label': 'Cancelled', 'timestamp': order.updated_at, 'done': True})
    else:
        current_index = status_order.index(order.status) if order.status in status_order else 0
        labels = {'pending': 'Pending', 'processing': 'Processing', 'shipped': 'Shipped', 'delivered': 'Delivered'}
        for i, s in enumerate(status_order):
            if i == 0:
                continue  # already added as "Order Placed"
            timeline.append({
                'label': labels[s],
                'timestamp': order.updated_at if i <= current_index else None,
                'done': i <= current_index,
            })

    return render(request, 'orders/order_detail.html', {
        'order': order,
        'business': business,
        'timeline': timeline,
    })

@login_required
def order_status_update(request, pk):
    business = get_user_business(request.user)
    order = get_object_or_404(Order, pk=pk, business=business)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            if new_status == 'cancelled':
                order.cancellation_reason = request.POST.get('cancellation_reason', '').strip()
            order.save()
    return redirect(request.META.get('HTTP_REFERER', 'order_list'))


@login_required
def order_notes_update(request, pk):
    business = get_user_business(request.user)
    order = get_object_or_404(Order, pk=pk, business=business)
    if request.method == 'POST':
        order.internal_notes = request.POST.get('internal_notes', '').strip()
        order.save()
        messages.success(request, 'Notes saved.')
    return redirect('order_detail', pk=order.id)

@login_required
def order_payment_update(request, pk):
    business = get_user_business(request.user)
    order = get_object_or_404(Order, pk=pk, business=business)
    if request.method == 'POST':
        new_payment_status = request.POST.get('payment_status')
        if new_payment_status in dict(Order.PAYMENT_STATUS_CHOICES):
            order.payment_status = new_payment_status
            order.save()
    return redirect(request.META.get('HTTP_REFERER', 'order_list'))

@login_required
def order_add(request):
    business = get_user_business(request.user)
    from products.models import Product
    products = Product.objects.filter(business=business) if business else []
    
    if request.method == 'POST':
        order = Order.objects.create(
            business=business,
            customer_name=request.POST.get('customer_name'),
            customer_email=request.POST.get('customer_email'),
            customer_phone=request.POST.get('customer_phone'),
            shipping_address=request.POST.get('shipping_address'),
            status=request.POST.get('status', 'pending'),
            payment_status=request.POST.get('payment_status', 'unpaid'),
        )
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        total = 0
        for pid, qty in zip(product_ids, quantities):
            if pid:
                product = Product.objects.get(id=pid)
                qty = int(qty or 1)
                OrderItem.objects.create(
                    order=order, product=product,
                    quantity=qty, unit_price=product.price
                )
                total += product.price * qty
        order.total_amount = total
        order.save()
        return redirect('order_list')

    return render(request, 'orders/order_list.html', {'products': products})

@login_required
def order_bulk_update(request):
    business = get_user_business(request.user)
    if request.method == 'POST':
        order_ids = request.POST.getlist('order_ids')
        new_status = request.POST.get('bulk_status')
        if order_ids and new_status in dict(Order.STATUS_CHOICES):
            orders_to_update = Order.objects.filter(id__in=order_ids, business=business)
            if new_status == 'cancelled':
                orders_to_update = orders_to_update.exclude(status='delivered')
            count = orders_to_update.update(status=new_status)
            messages.success(request, f'{count} order(s) updated to "{new_status}".')
    return redirect(request.META.get('HTTP_REFERER', 'order_list'))

@login_required
def order_delete(request, pk):
    business = get_user_business(request.user)
    get_object_or_404(Order, pk=pk, business=business).delete()
    return redirect('order_list')

def parse_date_filters(request):
    from datetime import timedelta
    date_range = request.GET.get('date_range', '30')
    date_from_str = request.GET.get('date_from', '')
    date_to_str = request.GET.get('date_to', '')
    
    start_date = None
    end_date = None
    today = timezone.now().date()
    
    if date_range == '7':
        start_date = today - timedelta(days=6)
        end_date = today
    elif date_range == '30':
        start_date = today - timedelta(days=29)
        end_date = today
    elif date_range == '90':
        start_date = today - timedelta(days=89)
        end_date = today
    elif date_range == 'custom':
        if date_from_str:
            try:
                start_date = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        if date_to_str:
            try:
                end_date = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            except ValueError:
                pass
    return start_date, end_date, date_range, date_from_str, date_to_str

@login_required
def export_orders_csv(request):
    business = get_user_business(request.user)
    orders = Order.objects.filter(business=business).order_by('-created_at') if business else Order.objects.none()

    start_date, end_date, date_range, date_from_str, date_to_str = parse_date_filters(request)
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer', 'Email', 'Phone', 'Channel', 'Total Amount', 'Status', 'Payment Status', 'Date'])

    for order in orders:
        writer.writerow([
            order.id, order.customer_name, order.customer_email or '',
            order.customer_phone or '', order.channel.name if order.channel else '',
            order.total_amount, order.get_status_display(),
            order.get_payment_status_display(), order.created_at.strftime('%Y-%m-%d')
        ])

    return response

from django.db.models import Count, Sum, Max

@login_required
def customer_list(request):
    business = get_user_business(request.user)
    orders_qs = Order.objects.filter(business=business).select_related('channel') if business else Order.objects.none()

    search_query = request.GET.get('q', '').strip().lower()
    sort_by = request.GET.get('sort', 'date-desc')  # default: latest activity first

    # Group ALL orders by identity key first (email if present, else phone)
    grouped = {}
    for order in orders_qs.order_by('-created_at'):
        key = (order.customer_email or '').strip() or (order.customer_phone or '').strip()
        if not key:
            continue

        if key not in grouped:
            grouped[key] = {
                'name': order.customer_name or 'Unknown',
                'email': order.customer_email or '',
                'phone': order.customer_phone or 'No phone on file',
                'total_orders': 0,
                'total_spent': 0,
                'last_order_date': None,
                'first_order_date': None,
                'order_ids': [],
                'orders': [],
            }

        entry = grouped[key]
        entry['total_orders'] += 1
        entry['total_spent'] += order.total_amount
        entry['order_ids'].append(str(order.id))
        if entry['last_order_date'] is None or order.created_at > entry['last_order_date']:
            entry['last_order_date'] = order.created_at
            entry['name'] = order.customer_name or entry['name']
            if order.customer_email:
                entry['email'] = order.customer_email
            if order.customer_phone:
                entry['phone'] = order.customer_phone

        if entry['first_order_date'] is None or order.created_at < entry['first_order_date']:
            entry['first_order_date'] = order.created_at

        entry['orders'].append({
            'id': order.id,
            'date': order.created_at.strftime('%b %d, %Y · %H:%M'),
            'channel': order.channel.name if order.channel else 'Manual',
            'amount': str(order.total_amount),
            'status': order.status,
            'status_display': order.get_status_display(),
        })

    # Build the full customer list (unfiltered) — used for stat cards, so search never affects totals
    all_customers = []
    for key, entry in grouped.items():
        if entry['total_orders'] >= 10:
            status = 'vip'
        elif entry['total_orders'] >= 2:
            status = 'returning'
        else:
            status = 'new'

        all_customers.append({
            'name': entry['name'],
            'email': entry['email'] or 'No email on file',
            'phone': entry['phone'],
            'total_orders': entry['total_orders'],
            'total_spent': entry['total_spent'],
            'last_order_date_obj': entry['last_order_date'],
            'last_order_date': entry['last_order_date'].strftime('%b %d, %Y') if entry['last_order_date'] else '',
            'status': status,
            'order_ids': entry['order_ids'],
            'order_history_json': json.dumps(entry['orders']),
        })

    # Stats are always computed from the FULL list, never the filtered/searched one
    total_customers = len(all_customers)
    new_count = sum(1 for c in all_customers if c['status'] == 'new')
    returning_count = sum(1 for c in all_customers if c['status'] == 'returning')
    vip_count = sum(1 for c in all_customers if c['status'] == 'vip')
    repeat_count = returning_count + vip_count
    
    repeat_rate = round(repeat_count / total_customers * 100, 1) if total_customers > 0 else 0
    avg_ltv = round(sum(c['total_spent'] for c in all_customers) / total_customers, 2) if total_customers > 0 else 0

    # 1. Genuinely time-based "New Customers": first-ever order date in last 30 days
    today = timezone.now().date()
    last_30_days_start = today - timezone.timedelta(days=29)
    new_customers_30d = sum(
        1 for key, entry in grouped.items()
        if entry['first_order_date'] and entry['first_order_date'].date() >= last_30_days_start
    )

    # Compare against prior 30-day period (days -59 to -30)
    prior_30_start = today - timezone.timedelta(days=59)
    prior_30_end = today - timezone.timedelta(days=30)
    new_customers_prior = sum(
        1 for key, entry in grouped.items()
        if entry['first_order_date'] and prior_30_start <= entry['first_order_date'].date() <= prior_30_end
    )

    if new_customers_prior > 0:
        pct = ((new_customers_30d - new_customers_prior) / new_customers_prior) * 100
        new_trend_str = f"{'+' if pct >= 0 else ''}{pct:.1f}% vs prior 30d"
        new_trend_up = pct >= 0
    else:
        new_trend_str = "No prior data"
        new_trend_up = True

    # 2. Daily time series for Customer Growth chart (last 30 days)
    growth_data = {}
    for i in range(30):
        day = today - timezone.timedelta(days=29 - i)
        growth_data[day] = 0

    for key, entry in grouped.items():
        if entry['first_order_date']:
            fdate = entry['first_order_date'].date()
            if fdate in growth_data:
                growth_data[fdate] += 1

    growth_labels = [d.strftime('%b %d') for d in sorted(growth_data.keys())]
    growth_values = [growth_data[d] for d in sorted(growth_data.keys())]

    growth_chart_json = json.dumps({
        'labels': growth_labels,
        'values': growth_values
    })

    # 3. Top Spender and Most Orders
    top_spender = None
    most_orders = None
    if all_customers:
        top_spender = max(all_customers, key=lambda x: x['total_spent'])
        most_orders = max(all_customers, key=lambda x: x['total_orders'])

    max_spent = float(top_spender['total_spent']) if top_spender and top_spender['total_spent'] > 0 else 1.0

    # Apply search filter (name, email, or order ID) to build the displayed list
    customers = []
    for c in all_customers:
        if search_query:
            matches_name = search_query in c['name'].lower()
            matches_email = search_query in c['email'].lower()
            matches_order_id = any(search_query == oid or search_query in oid for oid in c['order_ids'])
            if not (matches_name or matches_email or matches_order_id):
                continue
        customers.append(c)

    if sort_by == 'spent-desc':
        customers.sort(key=lambda x: x['total_spent'], reverse=True)
    elif sort_by == 'spent-asc':
        customers.sort(key=lambda x: x['total_spent'])
    elif sort_by == 'orders-desc':
        customers.sort(key=lambda x: x['total_orders'], reverse=True)
    else:  # date-desc, the default — latest activity first
        customers.sort(key=lambda x: x['last_order_date_obj'] or timezone.datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # Real Django pagination (10 per page)
    paginator = Paginator(customers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/customer_list.html', {
        'page_obj': page_obj,
        'total_customers': total_customers,
        'new_customers_30d': new_customers_30d,
        'new_trend_str': new_trend_str,
        'new_trend_up': new_trend_up,
        'repeat_rate': repeat_rate,
        'repeat_count': repeat_count,
        'vip_count': vip_count,
        'avg_ltv': avg_ltv,
        'search_query': request.GET.get('q', ''),
        'sort_by': sort_by,
        'has_customers': total_customers > 0,
        'has_results': len(customers) > 0,
        'business': business,
        'top_spender': top_spender,
        'most_orders': most_orders,
        'max_spent': max_spent,
        'growth_chart_json': growth_chart_json,
    })


def _relative_time(dt):
    diff = timezone.now() - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "Just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = int(seconds // 3600)
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(seconds // 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"


@login_required
def notifications_view(request):
    business = get_user_business(request.user)
    current_filter = request.GET.get('filter', 'all')

    notifications = []

    if business:
        from accounts.models import DismissedNotification
        dismissed = set(
            DismissedNotification.objects.filter(business=business)
            .values_list('notif_type', 'reference_id')
        )

        low_stock_products = Product.objects.filter(business=business, stock__lte=5).order_by('-created_at')
        for p in low_stock_products:
            if ('low-stock', p.id) not in dismissed:
                notifications.append({
                    'type': 'low-stock',
                    'product_id': p.id,
                    'product_title': p.title,
                    'stock': p.stock,
                    'timestamp': p.created_at,
                    'time_label': _relative_time(p.created_at),
                })

        recent_orders = Order.objects.filter(business=business).order_by('-created_at')[:20]
        for o in recent_orders:
            if ('new-order', o.id) not in dismissed:
                notifications.append({
                    'type': 'new-order',
                    'order_id': o.id,
                    'customer_name': o.customer_name,
                    'amount': o.total_amount,
                    'channel_name': o.channel.name if o.channel else 'Manual',
                    'timestamp': o.created_at,
                    'time_label': _relative_time(o.created_at),
                })

    notifications.sort(key=lambda x: x['timestamp'], reverse=True)

    if current_filter != 'all':
        notifications = [n for n in notifications if n['type'] == current_filter]

    # Calculate metrics respecting current filter
    total_alerts = len(notifications)
    low_stock_alerts = sum(1 for n in notifications if n['type'] == 'low-stock')
    new_orders_alerts = sum(1 for n in notifications if n['type'] == 'new-order')

    # Group notifications by date
    today_date = timezone.now().date()
    yesterday_date = today_date - timezone.timedelta(days=1)

    grouped_notifications = {
        'today': [],
        'yesterday': [],
        'earlier': []
    }
    for n in notifications:
        notif_date = n['timestamp'].date()
        if notif_date == today_date:
            grouped_notifications['today'].append(n)
        elif notif_date == yesterday_date:
            grouped_notifications['yesterday'].append(n)
        else:
            grouped_notifications['earlier'].append(n)

    notes = Note.objects.filter(business=business).order_by('-created_at') if business else Note.objects.none()

    return render(request, 'orders/notifications.html', {
        'notifications': notifications,
        'grouped_notifications': grouped_notifications,
        'total_alerts': total_alerts,
        'low_stock_alerts': low_stock_alerts,
        'new_orders_alerts': new_orders_alerts,
        'current_filter': current_filter,
        'business': business,
        'notes': notes,
    })


@login_required
def export_inventory_csv(request):
    business = get_user_business(request.user)
    products = Product.objects.filter(business=business).order_by('title') if business else Product.objects.none()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Product', 'Category', 'Price', 'Stock', 'Status', 'Date Added'])

    for p in products:
        writer.writerow([
            p.title,
            p.category.name if p.category else 'Uncategorized',
            p.price,
            p.stock,
            'Active' if p.is_active else 'Inactive',
            p.created_at.strftime('%Y-%m-%d'),
        ])

    return response


@login_required
def export_customers_csv(request):
    business = get_user_business(request.user)
    orders_qs = Order.objects.filter(business=business).exclude(customer_email__isnull=True).exclude(customer_email='') if business else Order.objects.none()

    start_date, end_date, date_range, date_from_str, date_to_str = parse_date_filters(request)
    if start_date:
        orders_qs = orders_qs.filter(created_at__date__gte=start_date)
    if end_date:
        orders_qs = orders_qs.filter(created_at__date__lte=end_date)

    grouped = (
        orders_qs.values('customer_email', 'customer_name', 'customer_phone')
        .annotate(total_orders=Count('id'), total_spent=Sum('total_amount'), last_order_date=Max('created_at'))
        .order_by('-total_spent')
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customer_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Customer Name', 'Email', 'Phone', 'Total Orders', 'Total Spent', 'Last Order Date'])

    for c in grouped:
        writer.writerow([
            c['customer_name'],
            c['customer_email'],
            c['customer_phone'] or '',
            c['total_orders'],
            c['total_spent'],
            c['last_order_date'].strftime('%Y-%m-%d') if c['last_order_date'] else '',
        ])

    return response

@login_required
def reports_view(request):
    business = get_user_business(request.user)
    
    start_date, end_date, date_range, date_from_str, date_to_str = parse_date_filters(request)
    
    orders_qs = Order.objects.filter(business=business) if business else Order.objects.none()
    products_qs = Product.objects.filter(business=business) if business else Product.objects.none()
    
    # Filter orders by range for dynamic counts
    orders_filtered = orders_qs
    if start_date:
        orders_filtered = orders_filtered.filter(created_at__date__gte=start_date)
    if end_date:
        orders_filtered = orders_filtered.filter(created_at__date__lte=end_date)

    # Recompute preview counts
    sales_count = orders_filtered.count()
    inventory_count = products_qs.count()
    customers_count = orders_filtered.exclude(customer_email__isnull=True).exclude(customer_email='').values('customer_email').distinct().count()
    invoices_count = orders_filtered.count()
    
    # Channel Revenue count
    channel_count = orders_filtered.values('channel_id').distinct().count()
    
    # Fulfillment status count
    fulfillment_count = orders_filtered.values('status').distinct().count()
    
    # Sales by Weekday count
    weekday_count = orders_filtered.annotate(weekday=ExtractWeekDay('created_at')).values('weekday').distinct().count()
    
    # Top Products count
    top_products_count = OrderItem.objects.filter(order__in=orders_filtered).values('product_id').distinct().count()
    
    # High-level snapshot metrics
    total_orders = orders_qs.count()
    total_products = products_qs.count()
    total_customers = orders_qs.exclude(customer_email__isnull=True).exclude(customer_email='').values('customer_email').distinct().count()

    return render(request, 'orders/reports.html', {
        'total_orders': total_orders,
        'total_products': total_products,
        'total_customers': total_customers,
        
        # Row counts
        'sales_count': sales_count,
        'inventory_count': inventory_count,
        'customers_count': customers_count,
        'invoices_count': invoices_count,
        'channel_count': channel_count,
        'fulfillment_count': fulfillment_count,
        'weekday_count': weekday_count,
        'top_products_count': top_products_count,
        
        # Filter state
        'date_range': date_range,
        'date_from': date_from_str,
        'date_to': date_to_str,
        'business': business,
    })

@login_required
def export_channel_revenue_csv(request):
    business = get_user_business(request.user)
    orders = Order.objects.filter(business=business) if business else Order.objects.none()

    start_date, end_date, date_range, date_from_str, date_to_str = parse_date_filters(request)
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    channels_qs = Channel.objects.filter(business=business) if business else Channel.objects.none()
    channels_dict = {c.id: c for c in channels_qs}

    channel_revs = orders.values('channel_id').annotate(revenue=Sum('total_amount'), count=Count('id')).order_by('-revenue')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="channel_revenue_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Channel', 'Revenue', 'Order Count'])

    for item in channel_revs:
        ch_id = item['channel_id']
        rev = float(item['revenue'] or 0.0)
        count = item['count']
        if ch_id is None:
            name = "Manual"
        else:
            ch = channels_dict.get(ch_id)
            name = ch.name if ch else f"Channel #{ch_id}"
        writer.writerow([name, round(rev, 2), count])
    return response

@login_required
def export_fulfillment_status_csv(request):
    business = get_user_business(request.user)
    orders = Order.objects.filter(business=business) if business else Order.objects.none()

    start_date, end_date, date_range, date_from_str, date_to_str = parse_date_filters(request)
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    total_orders = orders.count()
    status_choices = ['delivered', 'shipped', 'processing', 'pending', 'cancelled']
    status_counts = {s: orders.filter(status=s).count() for s in status_choices}

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="fulfillment_status_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Status', 'Order Count', 'Percentage'])

    for s in status_choices:
        count = status_counts[s]
        pct = round((count / total_orders * 100), 1) if total_orders > 0 else 0.0
        writer.writerow([s.capitalize(), count, f"{pct}%"])
    return response

@login_required
def export_sales_by_weekday_csv(request):
    business = get_user_business(request.user)
    orders = Order.objects.filter(business=business) if business else Order.objects.none()

    start_date, end_date, date_range, date_from_str, date_to_str = parse_date_filters(request)
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day_revenue = [0.0] * 7
    day_orders = [0] * 7

    try:
        weekday_data = (
            orders
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
        for o in orders:
            w = o.created_at.weekday()
            day_revenue[w] += float(o.total_amount)
            day_orders[w] += 1

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_by_weekday_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Day of Week', 'Revenue', 'Order Count'])

    for idx, day_name in enumerate(day_names):
        writer.writerow([day_name, round(day_revenue[idx], 2), day_orders[idx]])
    return response

@login_required
def export_top_products_csv(request):
    business = get_user_business(request.user)
    orders = Order.objects.filter(business=business) if business else Order.objects.none()

    start_date, end_date, date_range, date_from_str, date_to_str = parse_date_filters(request)
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)

    from collections import defaultdict
    product_sales = defaultdict(lambda: {'sold': 0, 'revenue': 0.0, 'product': None})
    for item in OrderItem.objects.filter(order__in=orders).select_related('product'):
        if item.product:
            key = item.product.id
            product_sales[key]['sold'] += item.quantity
            product_sales[key]['revenue'] += float(item.quantity * item.unit_price)
            product_sales[key]['product'] = item.product

    top_products_data = sorted(product_sales.values(), key=lambda x: x['revenue'], reverse=True)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="top_products_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Product', 'Units Sold', 'Revenue'])

    for p in top_products_data:
        writer.writerow([p['product'].title, p['sold'], round(p['revenue'], 2)])
    return response


@login_required
def print_invoices(request):
    business = get_user_business(request.user)
    orders = Order.objects.filter(business=business).order_by('-created_at') if business else Order.objects.none()
    return render(request, 'orders/print_invoices.html', {
        'orders': orders,
        'business': business,
    })


@login_required
def discounts_view(request):
    business = get_user_business(request.user)
    discounts = Discount.objects.filter(business=business).order_by('-created_at') if business else Discount.objects.none()

    today = timezone.now().date()
    active_codes_count = sum(1 for d in discounts if d.status == 'active')
    total_redemptions = sum(d.times_used for d in discounts)
    total_discount_given = "Not yet tracked"
    expiring_soon_count = sum(
        1 for d in discounts
        if d.status == 'active' and (d.expiry_date - today).days <= 7
    )

    products = Product.objects.filter(business=business) if business else Product.objects.none()
    categories = Category.objects.filter(business=business) if business else Category.objects.none()
    channels = Channel.objects.filter(business=business) if business else Channel.objects.none()

    return render(request, 'orders/discounts.html', {
        'discounts': discounts,
        'active_codes_count': active_codes_count,
        'total_redemptions': total_redemptions,
        'total_discount_given': total_discount_given,
        'expiring_soon_count': expiring_soon_count,
        'business': business,
        'products': products,
        'categories': categories,
        'channels': channels,
    })

@login_required
def discount_create(request):
    business = get_user_business(request.user)
    if request.method == 'POST' and business:
        code = request.POST.get('code', '').strip().upper()
        if Discount.objects.filter(business=business, code=code).exists():
            messages.error(request, f'Discount code "{code}" already exists.')
            return redirect('discounts_view')

        discount = Discount.objects.create(
            business=business,
            code=code,
            discount_type=request.POST.get('discount_type'),
            value=request.POST.get('value'),
            min_order_amount=request.POST.get('min_order_amount') or None,
            usage_limit=request.POST.get('usage_limit') or None,
            start_date=request.POST.get('start_date'),
            expiry_date=request.POST.get('expiry_date'),
            is_active=request.POST.get('is_active') == 'true',
        )

        product_ids = request.POST.getlist('applicable_products')
        category_ids = request.POST.getlist('applicable_categories')
        channel_ids = request.POST.getlist('applicable_channels')

        if product_ids:
            discount.applicable_products.set(product_ids)
        if category_ids:
            discount.applicable_categories.set(category_ids)
        if channel_ids:
            discount.applicable_channels.set(channel_ids)

        messages.success(request, f'Discount code "{code}" created successfully.')
    return redirect('discounts_view')



@login_required
def discount_update(request, pk):
    business = get_user_business(request.user)
    discount = get_object_or_404(Discount, pk=pk, business=business)
    if request.method == 'POST':
        discount.code = request.POST.get('code', '').strip().upper()
        discount.discount_type = request.POST.get('discount_type')
        discount.value = request.POST.get('value')
        discount.min_order_amount = request.POST.get('min_order_amount') or None
        discount.usage_limit = request.POST.get('usage_limit') or None
        discount.start_date = request.POST.get('start_date')
        discount.expiry_date = request.POST.get('expiry_date')
        discount.is_active = request.POST.get('is_active') == 'true'
        discount.save()

        product_ids = request.POST.getlist('applicable_products')
        category_ids = request.POST.getlist('applicable_categories')
        channel_ids = request.POST.getlist('applicable_channels')

        discount.applicable_products.set(product_ids)
        discount.applicable_categories.set(category_ids)
        discount.applicable_channels.set(channel_ids)

        messages.success(request, f'Discount code "{discount.code}" updated successfully.')
    return redirect('discounts_view')


@login_required
def discount_delete(request, pk):
    business = get_user_business(request.user)
    discount = get_object_or_404(Discount, pk=pk, business=business)
    discount.delete()
    return redirect('discounts_view')

@login_required
def export_discounts_csv(request):
    business = get_user_business(request.user)
    discounts = Discount.objects.filter(business=business).order_by('-created_at') if business else Discount.objects.none()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="discounts_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Code', 'Type', 'Value', 'Usage', 'Status', 'Expiry Date'])

    for d in discounts:
        usage_str = f"{d.times_used} / {d.usage_limit}" if d.usage_limit else f"{d.times_used} / Unlimited"
        writer.writerow([
            d.code,
            d.get_discount_type_display(),
            d.value,
            usage_str,
            d.status.capitalize(),
            d.expiry_date.strftime('%Y-%m-%d')
        ])

    return response

from django.http import JsonResponse
from accounts.models import DismissedNotification


@login_required
def dismiss_notification(request):
    business = get_user_business(request.user)
    if business and request.method == 'POST':
        notif_type = request.POST.get('notif_type')
        reference_id = request.POST.get('reference_id')
        if notif_type and reference_id:
            DismissedNotification.objects.get_or_create(
                business=business,
                notif_type=notif_type,
                reference_id=reference_id,
            )
    return JsonResponse({'success': True})

@login_required
def bulk_dismiss_notifications(request):
    business = get_user_business(request.user)
    if business and request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('items', [])
            for item in items:
                notif_type = item.get('type')
                ref_id = item.get('id')
                if notif_type and ref_id:
                    DismissedNotification.objects.get_or_create(
                        business=business,
                        notif_type=notif_type,
                        reference_id=ref_id,
                    )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def note_create(request):
    business = get_user_business(request.user)
    if business and request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Note.objects.create(
                business=business,
                content=content
            )
            messages.success(request, 'Note added successfully.')
    return redirect('notifications_view')

@login_required
def note_toggle_done(request, pk):
    business = get_user_business(request.user)
    if business and request.method == 'POST':
        note = get_object_or_404(Note, pk=pk, business=business)
        note.is_done = not note.is_done
        note.save()
    return redirect('notifications_view')

@login_required
def note_delete(request, pk):
    business = get_user_business(request.user)
    note = get_object_or_404(Note, pk=pk, business=business)
    note.delete()
    messages.success(request, 'Note deleted successfully.')
    return redirect('notifications_view')

@login_required
def note_update(request, pk):
    business = get_user_business(request.user)
    if business and request.method == 'POST':
        note = get_object_or_404(Note, pk=pk, business=business)
        content = request.POST.get('content', '').strip()
        if content:
            note.content = content
            note.save()
            messages.success(request, 'Note updated.')
    return redirect('notifications_view')