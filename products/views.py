from django.shortcuts import render, get_object_or_404, redirect
from django.utils.text import slugify
from .models import Product, Category, ProductVariant

def dashboard(request):
    total_products = Product.objects.count()
    low_stock = Product.objects.filter(stock__lte=5).count()
    recent_products = Product.objects.order_by('-created_at')[:5]
    return render(request, 'dashboard.html', {
        'total_products': total_products,
        'low_stock': low_stock,
        'recent_products': recent_products,
    })

def product_list(request):
    products = Product.objects.all().order_by('-created_at')
    total_products = products.count()
    active_products = products.filter(is_active=True).count()
    low_stock = products.filter(stock__lte=5).count()
    total_categories = Category.objects.count()
    return render(request, 'products/product_list.html', {
        'products': products,
        'total_products': total_products,
        'active_products': active_products,
        'low_stock': low_stock,
        'total_categories': total_categories,
    })

def product_add(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        category_id = request.POST.get('category')
        is_active = request.POST.get('is_active') == 'true'
        image = request.FILES.get('image')

        category = Category.objects.get(id=category_id) if category_id else None

        product = Product.objects.create(
            title=title,
            description=description,
            price=price,
            stock=stock,
            category=category,
            is_active=is_active,
            image=image,
        )

        # Handle variants
        names = request.POST.getlist('variant_name[]')
        prices = request.POST.getlist('variant_price[]')
        stocks = request.POST.getlist('variant_stock[]')
        for n, p, s in zip(names, prices, stocks):
            if n:
                ProductVariant.objects.create(
                    product=product, name=n,
                    price=p or 0, stock=s or 0
                )

        return redirect('product_list')

    return render(request, 'products/product_form.html', {'categories': categories})

def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()
    if request.method == 'POST':
        product.title = request.POST.get('title')
        product.description = request.POST.get('description', '')
        product.price = request.POST.get('price')
        product.stock = request.POST.get('stock')
        product.is_active = request.POST.get('is_active') == 'true'
        category_id = request.POST.get('category')
        product.category = Category.objects.get(id=category_id) if category_id else None
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
        product.save()
        return redirect('product_list')
    return render(request, 'products/product_form.html', {
        'product': product,
        'categories': categories
    })

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect('product_list')

def category_list(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name')
            slug = request.POST.get('slug') or slugify(name)
            Category.objects.create(name=name, slug=slug)
            return redirect('category_list')
    return render(request, 'products/category_list.html', {'categories': categories})

def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.slug = request.POST.get('slug') or slugify(category.name)
        category.save()
        return redirect('category_list')
    return render(request, 'products/category_list.html', {
        'categories': Category.objects.all(),
        'edit_category': category
    })

def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    return redirect('category_list')