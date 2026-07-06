from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User, BusinessProfile, SellerProfile
from django.utils.text import slugify

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')

# ── Login ─────────────────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        # Allow email login
        try:
            user_obj = User.objects.get(email=username)
            username = user_obj.username
        except User.DoesNotExist:
            pass
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': True, 'redirect': '/dashboard/'})
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'success': False}, status=400)
    return render(request, 'auth/login.html')

# ── Logout ────────────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('login')

# ── Register (Unified — Option A) ─────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        full_name     = request.POST.get('full_name', '')
        business_name = request.POST.get('business_name', '')
        email         = request.POST.get('email', '')
        password      = request.POST.get('password', '')
        password2     = request.POST.get('password2', '')

        # Validation
        if not all([full_name, business_name, email, password, password2]):
            messages.error(request, 'All fields are required.')
            return render(request, 'auth/register.html')

        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/register.html')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return render(request, 'auth/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'auth/register.html')

        # Generate unique username from email
        base_username = email.split('@')[0].lower()
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='business_owner',
        )
        # Set full name
        names = full_name.strip().split(' ', 1)
        user.first_name = names[0]
        user.last_name  = names[1] if len(names) > 1 else ''
        user.save()

        # Create BusinessProfile
        slug = slugify(business_name)
        original_slug = slug
        counter = 1
        while BusinessProfile.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1

        BusinessProfile.objects.create(
            user=user,
            business_name=business_name,
            slug=slug,
        )

        # Log them in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Handle AJAX (from landing page modal)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': True, 'redirect': '/dashboard/'})

        messages.success(request, f'Welcome to E-Com Orbit, {business_name}!')
        return redirect('dashboard')

    return render(request, 'auth/register.html')

# ── Keep old views as aliases for backward compatibility ───────────
def register_business(request):
    return register_view(request)

def register_seller(request):
    return register_view(request)