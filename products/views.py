from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from .models import Product, Category, ProductVariant
from accounts.models import BusinessProfile
from django.db.models import Sum, F


def get_user_business(user):
    """Helper — gets business profile for logged in user or None"""
    try:
        return BusinessProfile.objects.get(user=user)
    except BusinessProfile.DoesNotExist:
        return None

@login_required
def dashboard(request):
    business = get_user_business(request.user)
    if business:
        products = Product.objects.filter(business=business)
        from channels_integration.models import Channel
        channels = Channel.objects.filter(business=business)
        user_channels = channels.filter(is_active=True)[:5]
        active_channels = channels.filter(is_active=True).count()

        from orders.models import Order, OrderItem
        from django.db.models import Sum, F
        from datetime import timedelta
        from django.utils import timezone

        orders = Order.objects.filter(business=business)
        total_orders = orders.count()
        total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0
        pending_fulfillment = orders.filter(status__in=['pending', 'processing']).count()
        recent_orders = orders.select_related('channel').order_by('-created_at')[:5]

        # Order status breakdown for donut
        status_counts = {
            'delivered': orders.filter(status='delivered').count(),
            'shipped': orders.filter(status='shipped').count(),
            'processing': orders.filter(status='processing').count(),
            'pending': orders.filter(status='pending').count(),
            'cancelled': orders.filter(status='cancelled').count(),
        }

        # Mini 14-day revenue trend for Sales Overview chart
        today = timezone.now().date()
        date_range = [today - timedelta(days=i) for i in range(13, -1, -1)]
        daily_revenue = {d: 0 for d in date_range}
        for order in orders.filter(created_at__date__gte=date_range[0]):
            order_date = order.created_at.date()
            if order_date in daily_revenue:
                daily_revenue[order_date] += float(order.total_amount)

        mini_trend_labels = [d.strftime('%b %d') for d in date_range]
        mini_trend_data = [round(daily_revenue[d], 2) for d in date_range]

        from collections import defaultdict
        product_sales = defaultdict(lambda: {'sold': 0, 'revenue': 0, 'product': None})
        for item in OrderItem.objects.filter(order__business=business).select_related('product'):
            if item.product:
                key = item.product.id
                product_sales[key]['sold'] += item.quantity
                product_sales[key]['revenue'] += item.quantity * item.unit_price
                product_sales[key]['product'] = item.product

        top_products_data = sorted(product_sales.values(), key=lambda x: x['revenue'], reverse=True)[:5]
    else:
        products = Product.objects.none()
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

    total_products = products.count()
    low_stock = products.filter(stock__lte=5).count()
    recent_products = products.order_by('-created_at')[:5]

    import json

    return render(request, 'dashboard.html', {
        'business': business,
        'total_products': total_products,
        'low_stock': low_stock,
        'active_channels': active_channels,
        'recent_products': recent_products,
        'top_products': top_products_data,
        'user_channels': user_channels,
        'total_orders': total_orders,
        'pending_fulfillment': pending_fulfillment,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'status_counts': status_counts,
        'mini_trend_json': json.dumps({'labels': mini_trend_labels, 'data': mini_trend_data}),
        'status_counts_json': json.dumps(status_counts),
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

@login_required
def category_list(request):
    business = get_user_business(request.user)
    categories = Category.objects.filter(business=business)
    if request.method == 'POST':
        name = request.POST.get('name')
        slug = request.POST.get('slug') or slugify(name)
        # Make slug unique
        original_slug = slug
        counter = 1
        while Category.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1
        Category.objects.create(name=name, slug=slug, business=business)
        return redirect('category_list')
    return render(request, 'products/category_list.html', {
        'categories': categories,
        'business'  : business,
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
        'categories'   : Category.objects.filter(business=business),
        'edit_category': category,
        'business'     : business,
    })

@login_required
def category_delete(request, pk):
    business = get_user_business(request.user)
    get_object_or_404(Category, pk=pk, business=business).delete()
    return redirect('category_list')

