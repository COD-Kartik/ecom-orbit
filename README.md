[README.md](https://github.com/user-attachments/files/30531260/README.md)
# E-Com Orbit

**Sell Everywhere, Manage Anywhere.**

E-Com Orbit is a multi-tenant social-commerce SaaS platform that lets sellers manage products, orders, customers, and multi-channel sales — with live sync automation to WhatsApp Business.

🔗 **Live demo:** [ecom-orbit-chi.vercel.app](https://ecom-orbit-chi.vercel.app)

---

## Overview

Built during a summer internship at TechnoAce India, E-Com Orbit consolidates the operational chaos of running a small e-commerce business — separate spreadsheets, manual stock updates, disconnected order channels — into a single dashboard. The current channel integration focus is **WhatsApp Business Platform (Meta Cloud API)**, with automated two-way sync between the seller's catalog and their live WhatsApp storefront.

## Features

**Core commerce**
- Multi-tenant business accounts with a single unified registration/login flow
- Product catalog with categories, stock tracking, and **product variants** (size, color, etc.)
- Multi-image product galleries
- Order management with status tracking (pending → processing → shipped → delivered / cancelled), bulk actions, and a customer timeline
- Customer directory with automatic segmentation (new / returning / VIP) and lifetime value tracking
- Discount codes scoped to specific products, categories, or channels
- CSV exports and a reports dashboard (sales, inventory, channel revenue, fulfillment status)

**WhatsApp Business integration**
- Two-way catalog sync — publishing, editing (price/stock), or deleting a product automatically pushes to the seller's WhatsApp Commerce Catalog via Meta's `items_batch` API
- Product variants sync as individually orderable catalog items (grouped via `item_group_id`), so a customer can order "5 white, 3 black" as distinct line items
- Real-time order import — a WhatsApp order message creates an `Order` in the dashboard automatically, decrements the correct stock, and re-syncs availability back to WhatsApp
- Order status changes (shipped/delivered/cancelled) trigger a WhatsApp message to the customer via approved message templates
- Channel health monitoring — a site-wide banner and blocking modal alert the seller when a channel connection has expired and needs reconnecting, with one-click access to the reconnect flow

**Infrastructure**
- Media (avatars, product photos) served via Cloudinary
- Hosted PostgreSQL via Neon
- Deployed on Vercel with zero-config Django detection

## Tech Stack

- **Backend:** Django 6.0, Django REST Framework
- **Database:** PostgreSQL (Neon)
- **Frontend:** Bootstrap 5, Chart.js, vanilla JS
- **Media storage:** Cloudinary
- **Deployment:** Vercel
- **Integrations:** Meta WhatsApp Business Cloud API

## Getting Started

### Prerequisites
- Python 3.12+
- A PostgreSQL database (local or hosted)
- A Cloudinary account (for media storage)
- A Meta developer app with WhatsApp Business Platform configured (for channel sync features)

### Installation

```bash
git clone https://github.com/COD-Kartik/ecom-orbit.git
cd ecom-orbit

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

### Environment variables

Create a `.env` file in the project root:

```
SECRET_KEY=
DEBUG=True
DATABASE_URL=

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_CATALOG_ID=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=
```

### Run locally

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000`.

## Project Structure

```
ecom-orbit/
├── accounts/              # Auth, user & business profiles
├── products/               # Catalog, categories, variants, images
├── orders/                  # Orders, customers, discounts, notes
├── channels_integration/    # Channel sync, WhatsApp client, webhooks
├── analytics/               # Reporting
├── landing/                  # Public marketing site
├── static/css/                # Per-page stylesheets
├── templates/                  # Shared base templates
└── config/                      # Django project settings
```

## Status

Actively developed. Current focus: WhatsApp Business Platform integration, pending Meta business verification for full production messaging access.

## Author

Built by **Kartik Mathur** — 2nd-year B.Tech CSE (AI/ML), UPES Dehradun — as part of a summer internship at TechnoAce India.
