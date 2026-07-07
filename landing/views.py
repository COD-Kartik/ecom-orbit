from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings


def home_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing/home.html')


def features_page(request):
    return render(request, 'landing/features.html')


def why_orbit_page(request):
    return render(request, 'landing/why_orbit.html')


def how_it_works_page(request):
    return render(request, 'landing/how_it_works.html')


def pricing_page(request):
    return render(request, 'landing/pricing.html')


def success_stories_page(request):
    return render(request, 'landing/success_stories.html')


def about_page(request):
    return render(request, 'landing/about.html')


def contact_page(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', 'General Feedback')
        message_body = request.POST.get('message', '').strip()

        if name and email and message_body:
            try:
                send_mail(
                    subject=f"[E-Com Orbit Contact] {subject} — from {name}",
                    message=f"From: {name} <{email}>\n\n{message_body}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.EMAIL_HOST_USER],
                )
                messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
            except Exception:
                messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
        else:
            messages.error(request, "Please fill in all required fields.")

        return redirect('contact_page')

    return render(request, 'landing/contact.html')


def privacy_page(request):
    return render(request, 'landing/privacy.html')


def blog_page(request):
    return render(request, 'landing/blog.html')