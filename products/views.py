from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from .models import Product, Category, ProductVariant
from accounts.models import BusinessProfile
from django.db.models import Sum, F
from django.contrib import messages


def get_user_business(user):
    """Helper — gets business profile for logged in user or None"""
    try:
        return BusinessProfile.objects.get(user=user)
    except BusinessProfile.DoesNotExist:
        return None

@login_required
def dashboard(request):
    business = get_user_business(request.user)
    
    from django.db.models import Sum, Count, Q
    from datetime import timedelta
    from django.utils import timezone
    from collections import defaultdict
    import json
    from channels_integration.models import Channel, SyncLog

    # Fixed sensible 30-day default for time-series metrics
    today = timezone.now().date()
    start_date = today - timedelta(days=29)
    end_date = today
    date_range_label = "30 days"

    if business:
        products = Product.objects.filter(business=business)
        channels = Channel.objects.filter(business=business)
        user_channels = channels.filter(is_active=True)[:5]
        active_channels = channels.filter(is_active=True).count()

        from orders.models import Order, OrderItem

        # Base orders for current business
        base_orders = Order.objects.filter(business=business)

        # Filtered orders for time-series metrics (respects fixed 30-day range)
        filtered_orders = base_orders.filter(created_at__date__range=[start_date, end_date])

        # Metrics that respect time filters
        total_orders = filtered_orders.count()
        total_revenue = filtered_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        pending_fulfillment = filtered_orders.filter(status__in=['pending', 'processing']).count()
        recent_orders = filtered_orders.select_related('channel').order_by('-created_at')[:5]

        # Order status breakdown for donut chart
        status_counts = {
            'delivered': filtered_orders.filter(status='delivered').count(),
            'shipped': filtered_orders.filter(status='shipped').count(),
            'processing': filtered_orders.filter(status='processing').count(),
            'pending': filtered_orders.filter(status='pending').count(),
            'cancelled': filtered_orders.filter(status='cancelled').count(),
        }

        # Sales Overview line chart date range trend
        num_days = (end_date - start_date).days + 1
        date_range = [start_date + timedelta(days=i) for i in range(num_days)]
        daily_revenue = {d: 0.0 for d in date_range}
        
        for order in filtered_orders:
            order_date = order.created_at.date()
            if order_date in daily_revenue:
                daily_revenue[order_date] += float(order.total_amount)

        mini_trend_labels = [d.strftime('%b %d') for d in date_range]
        mini_trend_data = [round(daily_revenue[d], 2) for d in date_range]

        # Top Performing Products based on filtered orders
        product_sales = defaultdict(lambda: {'sold': 0, 'revenue': 0, 'product': None})
        for item in OrderItem.objects.filter(order__in=filtered_orders).select_related('product'):
            if item.product:
                key = item.product.id
                product_sales[key]['sold'] += item.quantity
                product_sales[key]['revenue'] += item.quantity * item.unit_price
                product_sales[key]['product'] = item.product

        top_products_data = sorted(product_sales.values(), key=lambda x: x['revenue'], reverse=True)[:5]

        # Channel Performance Bar Chart (Real aggregates)
        revenue_by_channel = filtered_orders.values('channel_id').annotate(revenue=Sum('total_amount'))
        rev_map = {item['channel_id']: float(item['revenue'] or 0.0) for item in revenue_by_channel}

        color_map = {
            'whatsapp': '#25D366',
            'flipkart': '#2874F0',
            'twitter': '#0f172a',
            'linkedin': '#0A66C2',
            'pinterest': '#E60023',
            'youtube': '#FF0000',
            'other': '#7c3aed',
        }

        perf_labels = []
        perf_data = []
        perf_colors = []

        # Add manual orders
        manual_rev = rev_map.get(None, 0.0)
        perf_labels.append("Manual")
        perf_data.append(round(manual_rev, 2))
        perf_colors.append('#64748b')

        # Add connected channels
        for ch in channels:
            perf_labels.append(ch.name)
            perf_data.append(round(rev_map.get(ch.id, 0.0), 2))
            platform_lower = (ch.platform_type or '').lower().strip()
            perf_colors.append(color_map.get(platform_lower, '#6366f1'))

        channel_performance_data = {
            'labels': perf_labels,
            'data': perf_data,
            'colors': perf_colors
        }

        # Real Operations Summary statistics
        recent_24h_orders = base_orders.filter(created_at__gte=timezone.now() - timedelta(hours=24)).count()
        attention_needed = channels.filter(connection_status='error').count()

        # Change 6: Real Sync Activity aggregation for products/orders over last 30 days
        sync_logs_qs = SyncLog.objects.filter(
            channel__business=business,
            created_at__date__range=[start_date, end_date]
        ).values('created_at__date', 'status').annotate(count=Count('id'))

        sync_by_date = {d: {'success': 0, 'failed': 0} for d in date_range}
        for log in sync_logs_qs:
            log_date = log['created_at__date']
            status = log['status']
            if log_date in sync_by_date:
                # Group both success and partial under success, failed under failed
                if status in ['success', 'partial']:
                    sync_by_date[log_date]['success'] += log['count']
                elif status == 'failed':
                    sync_by_date[log_date]['failed'] += log['count']

        sync_success = [sync_by_date[d]['success'] for d in date_range]
        sync_failed = [sync_by_date[d]['failed'] for d in date_range]
        
        total_success = sum(sync_success)
        total_failed = sum(sync_failed)
        total_syncs = total_success + total_failed

        if total_syncs > 0:
            success_percent = round((total_success / total_syncs) * 100, 1)
            failed_percent = round((total_failed / total_syncs) * 100, 1)
        else:
            success_percent = 0.0
            failed_percent = 0.0

        sync_donut_data = {
            'success_count': total_success,
            'failed_count': total_failed,
            'success_percent': success_percent,
            'failed_percent': failed_percent,
            'total_syncs': total_syncs
        }

        # Per-channel failed-sync breakdown for Sync Activity card
        channel_sync_breakdown = []
        sync_by_channel = SyncLog.objects.filter(
            channel__business=business,
            created_at__date__range=[start_date, end_date],
            status='failed'
        ).values('channel__name').annotate(fail_count=Count('id')).order_by('-fail_count')

        for row in sync_by_channel:
            channel_sync_breakdown.append({'name': row['channel__name'] or 'Unknown', 'count': row['fail_count']})

        # Real Operations Summary statistics
        recent_24h_orders = base_orders.filter(created_at__gte=timezone.now() - timedelta(hours=24)).count()
        attention_needed = channels.filter(connection_status='error').count()

        # Reporting range label (today minus 30 days to today)
        start_label = start_date.strftime('%d %b %Y')
        end_label = end_date.strftime('%d %b %Y')
        reporting_range = f"{start_label} – {end_label}"
    else:
        products = Product.objects.none()
        channels = Channel.objects.none()
        user_channels = []
        active_channels = 0
        total_orders = 0
        total_revenue = 0
        pending_fulfillment = 0
        recent_orders = []
        top_products_data = []
        status_counts = {'delivered': 0, 'shipped': 0, 'processing': 0, 'pending': 0, 'cancelled': 0}
        mini_trend_labels = []
        mini_trend_data = []
        channel_performance_data = {'labels': [], 'data': [], 'colors': []}
        recent_24h_orders = 0
        attention_needed = 0
        sync_donut_data = {'success_count': 0, 'failed_count': 0, 'success_percent': 0.0, 'failed_percent': 0.0, 'total_syncs': 0}
        total_syncs = 0
        channel_sync_breakdown = []
        reporting_range = ""

    total_products = products.count()
    low_stock = products.filter(stock__lte=5).count()
    recent_products = products.order_by('-created_at')[:5]

    return render(request, 'dashboard.html', {
        'business': business,
        'total_products': total_products,
        'low_stock': low_stock,
        'active_channels': active_channels,
        'recent_products': recent_products,
        'top_products': top_products_data,
        'user_channels': user_channels,
        'all_channels': channels,
        'total_orders': total_orders,
        'pending_fulfillment': pending_fulfillment,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'status_counts': status_counts,
        
        # JSON feeds
        'mini_trend_json': json.dumps({'labels': mini_trend_labels, 'data': mini_trend_data}),
        'status_counts_json': json.dumps(status_counts),
        'channel_performance_json': json.dumps(channel_performance_data),
        'sync_donut_data': sync_donut_data,
        'sync_donut_json': json.dumps(sync_donut_data),
        'sync_has_data': total_syncs > 0,
        'total_syncs': total_syncs,
        'channel_sync_breakdown': channel_sync_breakdown,
        
        # Operations Summary Feed
        'recent_24h_orders': recent_24h_orders,
        'attention_needed': attention_needed,
        
        # Fixed 30-day metadata
        'selected_date_range': date_range_label,
        'date_range_label': date_range_label,
        'reporting_range': reporting_range,
    })


@login_required
def product_list(request):
    business = get_user_business(request.user)
    products = Product.objects.filter(business=business).order_by('-created_at') if business else Product.objects.none()

    search_query = request.GET.get('q', '').strip()
    if search_query:
        products = products.filter(title__icontains=search_query)

    from channels_integration.models import ProductListing
    listing_counts = {}
    for p in products:
        listing_counts[p.id] = ProductListing.objects.filter(product=p, status='published').count()

    total_products = Product.objects.filter(business=business).count() if business else 0
    active_products = Product.objects.filter(business=business, is_active=True).count() if business else 0
    low_stock = Product.objects.filter(business=business, stock__lte=5).count() if business else 0
    inventory_value = Product.objects.filter(business=business).aggregate(
        total=Sum(F('price') * F('stock'))
    )['total'] or 0 if business else 0
    return render(request, 'products/product_list.html', {
        'products': products,
        'listing_counts': listing_counts,
        'total_products': total_products,
        'active_products': active_products,
        'low_stock': low_stock,
        'inventory_value': inventory_value,
        'search_query': search_query,
        'business': business,
    })

@login_required
def product_add(request):
    business   = get_user_business(request.user)
    categories = Category.objects.filter(business=business)
    if request.method == 'POST':
        title       = request.POST.get('title')
        description = request.POST.get('description', '')
        price       = request.POST.get('price')
        stock       = request.POST.get('stock')
        category_id = request.POST.get('category')
        is_active   = request.POST.get('is_active') == 'true'
        image       = request.FILES.get('image')
        category    = Category.objects.get(id=category_id) if category_id else None
        product = Product.objects.create(
            title=title, description=description,
            price=price, stock=stock,
            category=category, is_active=is_active,
            image=image, business=business,
        )
        names  = request.POST.getlist('variant_name[]')
        prices = request.POST.getlist('variant_price[]')
        stocks = request.POST.getlist('variant_stock[]')
        for n, p, s in zip(names, prices, stocks):
            if n:
                ProductVariant.objects.create(
                    product=product, name=n,
                    price=p or 0, stock=s or 0
                )
        return redirect('product_list')
    return render(request, 'products/product_form.html', {
        'categories': categories,
        'business'  : business,
    })

@login_required
def product_edit(request, pk):
    business = get_user_business(request.user)
    product  = get_object_or_404(Product, pk=pk, business=business)
    categories = Category.objects.filter(business=business)
    if request.method == 'POST':
        product.title       = request.POST.get('title')
        product.description = request.POST.get('description', '')
        product.price       = request.POST.get('price')
        product.stock       = request.POST.get('stock')
        product.is_active   = request.POST.get('is_active') == 'true'
        category_id = request.POST.get('category')
        product.category = Category.objects.get(id=category_id) if category_id else None
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
        product.save()
        return redirect('product_list')
    return render(request, 'products/product_form.html', {
        'product'   : product,
        'categories': categories,
        'business'  : business,
    })

@login_required
def product_delete(request, pk):
    business = get_user_business(request.user)
    product  = get_object_or_404(Product, pk=pk, business=business)
    product.delete()
    return redirect('product_list')

from django.db.models import Count

@login_required
def category_list(request):
    business = get_user_business(request.user)
    categories = Category.objects.filter(business=business).annotate(product_count=Count('product'))
    if request.method == 'POST':
        pk = request.POST.get('category_id')
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug') or slugify(name)

        if pk:
            category = get_object_or_404(Category, pk=pk, business=business)
            duplicate = Category.objects.filter(business=business, name__iexact=name).exclude(pk=pk).exists()
            if duplicate:
                messages.error(request, f'A category named "{name}" already exists.')
                return redirect('category_list')
            category.name = name
            category.slug = slug or slugify(name)
            category.save()
        else:
            if Category.objects.filter(business=business, name__iexact=name).exists():
                messages.error(request, f'A category named "{name}" already exists.')
                return redirect('category_list')
            original_slug = slug
            counter = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1
            Category.objects.create(name=name, slug=slug, business=business)
        return redirect('category_list')

    return render(request, 'products/category_list.html', {
        'categories': categories,
        'business': business,
    })

@login_required
def category_edit(request, pk):
    business = get_user_business(request.user)
    category = get_object_or_404(Category, pk=pk, business=business)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.slug = request.POST.get('slug') or slugify(category.name)
        category.save()
        return redirect('category_list')
    return render(request, 'products/category_list.html', {
        'categories': Category.objects.filter(business=business).annotate(product_count=Count('product')),
        'edit_category': category,
        'business': business,
    })

@login_required
def category_delete(request, pk):
    business = get_user_business(request.user)
    get_object_or_404(Category, pk=pk, business=business).delete()
    return redirect('category_list')

