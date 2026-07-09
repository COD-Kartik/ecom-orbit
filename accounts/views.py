import random
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
from .models import User, BusinessProfile


def get_user_business(user):
    try:
        return BusinessProfile.objects.get(user=user)
    except BusinessProfile.DoesNotExist:
        return None


def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


def generate_and_send_code(user):
    code = str(random.randint(100000, 999999))
    user.verification_code = code
    user.verification_code_created_at = timezone.now()
    user.save()

    subject = "Your E-Com Orbit verification code"
    message = (
        f"Hi {user.first_name or user.username},\n\n"
        f"Your verification code is: {code}\n\n"
        f"This code expires in 10 minutes.\n\n"
        f"If you didn't request this, you can ignore this email."
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])


# ── Login ─────────────────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user_obj = User.objects.get(email=username)
            username = user_obj.username
        except User.DoesNotExist:
            user_obj = None

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('dashboard')
        else:
            if user_obj and not user_obj.is_active:
                messages.error(request, 'Please verify your email before signing in.')
            else:
                messages.error(request, 'Incorrect email or password. Please try again.')
    return render(request, 'auth/login.html')


# ── Logout ────────────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('landing')


# ── Register ──────────────────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        full_name     = request.POST.get('full_name', '')
        business_name = request.POST.get('business_name', '')
        email         = request.POST.get('email', '')
        password      = request.POST.get('password', '')
        password2     = request.POST.get('password2', '')

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

        base_username = email.split('@')[0].lower()
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='business_owner',
        )
        user.is_active = False
        names = full_name.strip().split(' ', 1)
        user.first_name = names[0]
        user.last_name  = names[1] if len(names) > 1 else ''
        user.save()

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

        generate_and_send_code(user)
        request.session['pending_verification_email'] = email
        return redirect('verify_code')

    return render(request, 'auth/register.html')


# ── Code Verification ────────────────────────────────────────────
def verify_code_view(request):
    email = request.session.get('pending_verification_email')
    if not email:
        return redirect('register')

    if request.method == 'POST':
        entered_code = request.POST.get('code', '').strip()
        try:
            user = User.objects.get(email=email, is_active=False)
        except User.DoesNotExist:
            messages.error(request, 'Something went wrong. Please register again.')
            return redirect('register')

        if not user.verification_code:
            messages.error(request, 'No verification code found. Please request a new one.')
            return render(request, 'auth/verify_code.html', {'email': email})

        expiry_time = user.verification_code_created_at + timedelta(minutes=10)
        if timezone.now() > expiry_time:
            messages.error(request, 'This code has expired. Please request a new one.')
            return render(request, 'auth/verify_code.html', {'email': email})

        if entered_code == user.verification_code:
            user.is_active = True
            user.verification_code = None
            user.save()
            del request.session['pending_verification_email']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Email verified! Welcome to E-Com Orbit.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Incorrect code. Please try again.')

    return render(request, 'auth/verify_code.html', {'email': email})


def resend_verification(request):
    email = request.session.get('pending_verification_email') or request.POST.get('email')
    if email:
        try:
            user = User.objects.get(email=email, is_active=False)
            generate_and_send_code(user)
            messages.success(request, 'A new verification code has been sent.')
        except User.DoesNotExist:
            pass
    return render(request, 'auth/verify_code.html', {'email': email})


def demo_dashboard(request):
    return render(request, 'demo_dashboard.html')

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password


@login_required
def settings_view(request):
    business = get_user_business(request.user)
    return render(request, 'accounts/settings.html', {
        'business': business,
    })


@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()

        names = full_name.split(' ', 1)
        user.first_name = names[0]
        user.last_name = names[1] if len(names) > 1 else ''
        user.phone = phone

        if request.FILES.get('profile_picture'):
            user.profile_picture = request.FILES.get('profile_picture')

        user.save()
        messages.success(request, 'Profile updated successfully.')
    return redirect('settings')


@login_required
def update_business(request):
    business = get_user_business(request.user)
    if request.method == 'POST' and business:
        business.business_name = request.POST.get('business_name', business.business_name).strip()
        business.business_phone = request.POST.get('business_phone', '').strip()
        business.address = request.POST.get('address', '').strip()
        business.tax_id = request.POST.get('tax_id', '').strip()
        business.description = request.POST.get('description', '').strip()

        if request.FILES.get('logo'):
            business.logo = request.FILES.get('logo')

        business.save()
        messages.success(request, 'Business information updated successfully.')
    return redirect('settings')


@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not check_password(current_password, request.user.password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('settings')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('settings')

        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters.')
            return redirect('settings')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)  # keeps user logged in after password change
        messages.success(request, 'Password updated successfully.')
    return redirect('settings')


@login_required
def delete_account(request):
    if request.method == 'POST':
        business = get_user_business(request.user)
        typed_name = request.POST.get('confirm_business_name', '').strip()

        if business and typed_name == business.business_name:
            user = request.user
            logout(request)
            user.delete()  # cascades to delete BusinessProfile, Products, Orders, etc.
            messages.success(request, 'Your account has been permanently deleted.')
            return redirect('landing')
        else:
            messages.error(request, 'Business name did not match. Account not deleted.')
            return redirect('settings')
    return redirect('settings')

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            user = User.objects.get(email=email, is_active=True)
            generate_and_send_code(user)
            request.session['reset_email'] = email
            return redirect('reset_password')
        except User.DoesNotExist:
            messages.error(request, "No active account found with that email.")
            return render(request, 'auth/forgot_password.html')

    return render(request, 'auth/forgot_password.html')


def reset_password_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')

    if request.method == 'POST':
        entered_code = request.POST.get('code', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            messages.error(request, 'Something went wrong. Please try again.')
            return redirect('forgot_password')

        if not user.verification_code:
            messages.error(request, 'No reset code found. Please request a new one.')
            return render(request, 'auth/reset_password.html', {'email': email})

        expiry_time = user.verification_code_created_at + timedelta(minutes=10)
        if timezone.now() > expiry_time:
            messages.error(request, 'This code has expired. Please request a new one.')
            return render(request, 'auth/reset_password.html', {'email': email})

        if entered_code != user.verification_code:
            messages.error(request, 'Incorrect code. Please try again.')
            return render(request, 'auth/reset_password.html', {'email': email})

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/reset_password.html', {'email': email})

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return render(request, 'auth/reset_password.html', {'email': email})

        user.set_password(new_password)
        user.verification_code = None
        user.save()
        del request.session['reset_email']

        messages.success(request, 'Password reset successfully. Please sign in with your new password.')
        return redirect('login')

    return render(request, 'auth/reset_password.html', {'email': email})


def resend_reset_code(request):
    email = request.session.get('reset_email')
    if email:
        try:
            user = User.objects.get(email=email, is_active=True)
            generate_and_send_code(user)
            messages.success(request, 'A new reset code has been sent.')
        except User.DoesNotExist:
            pass
    return render(request, 'auth/reset_password.html', {'email': email})

from django.http import JsonResponse
from django.utils import timezone


@login_required
def mark_notifications_viewed(request):
    business = get_user_business(request.user)
    if business and request.method == 'POST':
        business.notifications_last_viewed = timezone.now()
        business.save()
    return JsonResponse({'success': True})