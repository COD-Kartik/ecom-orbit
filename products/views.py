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
        channels      = Channel.objects.filter(business=business)
        user_channels = channels.filter(is_active=True)[:5]
        active_channels = channels.filter(is_active=True).count()
    else:
        products        = Product.objects.none()
        user_channels   = []
        active_channels = 0

    total_products  = products.count()
    low_stock       = products.filter(stock__lte=5).count()
    recent_products = products.order_by('-created_at')[:5]
    top_products    = products.order_by('-stock')[:5]

    return render(request, 'dashboard.html', {
        'business'       : business,
        'total_products' : total_products,
        'low_stock'      : low_stock,
        'active_channels': active_channels,
        'recent_products': recent_products,
        'top_products'   : top_products,
        'user_channels'  : user_channels,
        'total_orders'   : 0,
        'total_customers': 0,
        'total_revenue'  : 0,
        'recent_orders'  : [],
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

