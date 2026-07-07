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

    if status_filter:
        orders = orders.filter(status=status_filter)
    if search_query:
        orders = orders.filter(customer_name__icontains=search_query)

    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'total_orders': orders.count(),
        'pending_count': orders.filter(status='pending').count(),
        'processing_count': orders.filter(status='processing').count(),
        'shipped_count': orders.filter(status='shipped').count(),
        'delivered_count': orders.filter(status='delivered').count(),
        'cancelled_count': orders.filter(status='cancelled').count(),
        'current_status': status_filter or '',
        'search_query': search_query or '',
    })

@login_required
def order_detail(request, pk):
    business = get_user_business(request.user)
    order = get_object_or_404(Order, pk=pk, business=business)
    return render(request, 'orders/order_detail.html', {'order': order})

@login_required
def order_status_update(request, pk):
    business = get_user_business(request.user)
    order = get_object_or_404(Order, pk=pk, business=business)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
    return redirect(request.META.get('HTTP_REFERER', 'order_list'))

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

    return render(request, 'orders/order_form.html', {'products': products})

@login_required
def order_delete(request, pk):
    business = get_user_business(request.user)
    get_object_or_404(Order, pk=pk, business=business).delete()
    return redirect('order_list')

@login_required
def export_orders_csv(request):
    business = get_user_business(request.user)
    orders = Order.objects.filter(business=business).order_by('-created_at') if business else Order.objects.none()

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
    orders_qs = (
        Order.objects.filter(business=business)
        .exclude(customer_email__isnull=True)
        .exclude(customer_email='')
        if business else Order.objects.none()
    )

    grouped = (
        orders_qs.values('customer_email', 'customer_name', 'customer_phone')
        .annotate(
            total_orders=Count('id'),
            total_spent=Sum('total_amount'),
            last_order_date=Max('created_at'),
        )
        .order_by('-total_spent')
    )

    search_query = request.GET.get('q', '').strip().lower()
    sort_by = request.GET.get('sort', 'spent-desc')

    customers = []
    for c in grouped:
        if c['total_orders'] >= 10:
            status = 'vip'
        elif c['total_orders'] >= 2:
            status = 'returning'
        else:
            status = 'new'

        if search_query and search_query not in (c['customer_name'] or '').lower() and search_query not in (c['customer_email'] or '').lower():
            continue

        customer_orders = orders_qs.filter(customer_email=c['customer_email']).select_related('channel').order_by('-created_at')
        order_history = [
            {
                'id': o.id,
                'date': o.created_at.strftime('%b %d, %Y · %H:%M'),
                'channel': o.channel.name if o.channel else 'Manual',
                'amount': str(o.total_amount),
                'status': o.status,
                'status_display': o.get_status_display(),
            }
            for o in customer_orders
        ]

        customers.append({
            'name': c['customer_name'] or 'Unknown',
            'email': c['customer_email'],
            'phone': c['customer_phone'] or 'No phone on file',
            'total_orders': c['total_orders'],
            'total_spent': c['total_spent'],
            'last_order_date': c['last_order_date'].strftime('%b %d, %Y') if c['last_order_date'] else '',
            'status': status,
            'order_history_json': json.dumps(order_history),
        })

    if sort_by == 'spent-asc':
        customers.sort(key=lambda x: x['total_spent'])
    elif sort_by == 'orders-desc':
        customers.sort(key=lambda x: x['total_orders'], reverse=True)
    elif sort_by == 'date-desc':
        customers.sort(key=lambda x: x['last_order_date'], reverse=True)

    total_customers = len(customers)
    new_count = sum(1 for c in customers if c['status'] == 'new')
    returning_count = sum(1 for c in customers if c['status'] == 'returning')
    vip_count = sum(1 for c in customers if c['status'] == 'vip')
    repeat_rate = round((returning_count + vip_count) / total_customers * 100, 1) if total_customers > 0 else 0
    avg_ltv = round(sum(c['total_spent'] for c in customers) / total_customers, 2) if total_customers > 0 else 0

    return render(request, 'orders/customer_list.html', {
        'customers': customers,
        'total_customers': total_customers,
        'new_count': new_count,
        'repeat_rate': repeat_rate,
        'avg_ltv': avg_ltv,
        'search_query': request.GET.get('q', ''),
        'sort_by': sort_by,
        'has_customers': total_customers > 0,
        'business': business,
    })