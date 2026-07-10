from django.shortcuts import render, redirect
from django.http import Http404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings


def home_page(request):
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


def terms_page(request):
    return render(request, 'landing/terms.html')


def cookie_policy_page(request):
    return render(request, 'landing/cookie_policy.html')


def blog_page(request):
    return render(request, 'landing/blog.html')


# ── Blog post content store ──────────────────────────────────────
# Kept as structured data here rather than a database model, since
# there's no CMS/backend for blog content — just two genuine, complete
# articles for now.
BLOG_POSTS = {
    'signs-ready-for-multichannel-selling': {
        'title': "5 Signs You're Ready for Multi-Channel Selling",
        'category': 'Growth',
        'date': 'Jun 12, 2026',
        'read_time': '4 min',
        'excerpt': "If you're consistently selling out on one platform, it might be time to expand — here's how to know you're ready, and what to prepare before you do.",
        'content': [
            {'type': 'paragraph', 'text': "Expanding to a second or third sales channel feels exciting, but timing matters. Move too early and you'll spread yourself thin trying to manage listings you can't keep up with. Move too late and you'll leave real revenue on the table. Here are five signs that tell you it's genuinely time to expand."},

            {'type': 'heading', 'text': '1. You regularly sell out within days of restocking'},
            {'type': 'paragraph', 'text': "If your current channel consistently sells through inventory faster than you can restock, that's strong evidence of unmet demand. A second channel doesn't create new customers out of nowhere — but it does let existing demand reach you through more doors."},

            {'type': 'heading', 'text': '2. Customers are already asking where else they can find you'},
            {'type': 'paragraph', 'text': "Pay attention to comments and DMs. If people are regularly asking \"do you ship internationally?\" or \"are you on Amazon?\", that's a direct signal — your audience is already trying to buy from you elsewhere. Ignoring that is turning away money."},

            {'type': 'heading', 'text': '3. Your current channel has a ceiling you can feel'},
            {'type': 'paragraph', 'text': "Every platform has algorithmic reach limits, fee structures, and audience overlap. If your growth has plateaued despite consistent effort — more posts, better photos, active engagement — you may be running into that channel's natural ceiling rather than a marketing problem."},

            {'type': 'heading', 'text': '4. You have systems, not just spreadsheets'},
            {'type': 'paragraph', 'text': "This is the practical readiness check. Multi-channel selling multiplies your operational load — more listings to update, more orders to track, more customer messages to answer. Before expanding, make sure you have a real system (not a growing pile of spreadsheets) for inventory and order tracking."},

            {'type': 'heading', 'text': '5. You can answer: what happens when I sell the last unit?'},
            {'type': 'paragraph', 'text': "This is the single most common failure point for new multi-channel sellers: overselling. If a customer buys your last unit on Instagram, does your Facebook listing update automatically, or does someone else buy the same \"last unit\" an hour later? If you don't have a confident answer, that's the one thing to solve before adding a second channel."}
        ],
    },
    'true-cost-of-overselling': {
        'title': 'The True Cost of Overselling (And How to Avoid It)',
        'category': 'Inventory Tips',
        'date': 'Jun 28, 2026',
        'read_time': '5 min',
        'excerpt': "Overselling doesn't just cost you a refund — it costs you trust, reviews, and repeat customers. Here's how real-time inventory sync prevents it.",
        'content': [
            {'type': 'paragraph', 'text': "Overselling happens when the same unit of stock gets sold to two different customers on two different channels before anyone catches the mismatch. It feels like a small operational hiccup. In reality, it's one of the most expensive mistakes a growing seller can make — and the cost goes far beyond the refund."},

            {'type': 'heading', 'text': 'The visible cost: refunds and cancellations'},
            {'type': 'paragraph', 'text': "The most obvious cost is the money you have to give back, plus any payment processing fees you don't recover. But this is genuinely the smallest part of the problem."},

            {'type': 'heading', 'text': 'The invisible cost: trust'},
            {'type': 'paragraph', 'text': "Think about the experience from the customer's side. They found your product, got excited, paid for it — and then received a message saying it's actually not available. That disappointment doesn't just disappear. Even if you refund promptly and apologize sincerely, you've taught that customer that your stock numbers can't be trusted."},

            {'type': 'heading', 'text': 'The compounding cost: reviews and reputation'},
            {'type': 'paragraph', 'text': 'A canceled order rarely stays private. It frequently shows up as a public review or comment: "Ordered this and they canceled saying it was out of stock." Unlike a slow-shipping complaint, this specific type of review signals a deeper problem to future buyers — that your inventory management itself is unreliable.'},

            {'type': 'heading', 'text': 'Why this problem gets worse as you grow, not better'},
            {'type': 'list', 'items': [
                "More channels mean more places stock counts can drift out of sync",
                "Flash sales and promotions concentrate demand into short windows, increasing collision risk",
                "Manual updates get slower to perform exactly when speed matters most",
                "The more successful a product is, the more likely two customers try to buy your last unit simultaneously",
            ]},

            {'type': 'heading', 'text': 'The actual fix: real-time, automatic sync'},
            {'type': 'paragraph', 'text': "The only reliable solution is removing the manual step entirely. When a sale happens on any connected channel, your stock count needs to update everywhere else automatically and immediately — not at the end of the day, not \"when you get a chance,\" but the moment the order is placed. This is exactly the problem centralized inventory management tools like E-Com Orbit are built to solve: one source of truth for stock, synced continuously across every channel you sell on."},
        ],
    },
}

def blog_post_detail(request, slug):
    post = BLOG_POSTS.get(slug)
    if not post:
        raise Http404("Blog post not found")
    post = {**post, 'slug': slug}
    return render(request, 'landing/blog_post.html', {'post': post})