import requests
from django.conf import settings


def send_whatsapp_test_message(recipient_number):
    """
    Sends Meta's pre-approved 'hello_world' template message to verify
    that our WhatsApp credentials (token, phone number ID) are valid
    and the connection actually works end-to-end.

    recipient_number must be in international format, no '+', no spaces
    (e.g. '917737057335').
    """
    url = f"{settings.WHATSAPP_API_BASE_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

    headers = {
        'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
        'Content-Type': 'application/json',
    }

    payload = {
        'messaging_product': 'whatsapp',
        'to': recipient_number,
        'type': 'template',
        'template': {
            'name': 'hello_world',
            'language': {'code': 'en_US'},
        },
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        message_id = data.get('messages', [{}])[0].get('id')
        return {'success': True, 'message_id': message_id, 'response': data}
    else:
        return {'success': False, 'status_code': response.status_code, 'error': response.text}
    

def check_whatsapp_connection():
    """
    Verifies WhatsApp credentials are valid with zero side effects —
    a GET request to fetch our own phone number's metadata. No message
    is sent, unlike send_whatsapp_test_message(). This mirrors what
    get_flipkart_access_token() does for Flipkart: prove the connection
    works without spamming anyone.
    """
    url = f"{settings.WHATSAPP_API_BASE_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}"

    headers = {
        'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return {
            'success': True,
            'display_phone_number': data.get('display_phone_number'),
            'verified_name': data.get('verified_name'),
        }
    else:
        return {'success': False, 'status_code': response.status_code, 'error': response.text}
    

def push_product_to_whatsapp(product, public_base_url):
    """
    Creates or updates a product in the Meta Commerce Catalog using the
    items_batch endpoint. Field names here (id, title, image_link, link)
    match items_batch's specific schema — NOT the same as the separate
    /batch endpoint, which uses different field names (retailer_id, name,
    image_url). Confirmed against Meta's documented example.

    public_base_url: current ngrok URL, passed in explicitly since ngrok
    URLs change on restart.
    """
    url = f"{settings.WHATSAPP_API_BASE_URL}/{settings.WHATSAPP_CATALOG_ID}/items_batch"

    headers = {
        'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
    }

    if not product.image:
        return {'success': False, 'status_code': None, 'error': 'Product has no image — WhatsApp catalog requires an image.'}

    retailer_id = f"ECOMORBIT-{product.id}"
    image_url = f"{public_base_url}{product.image.url}"

    item_data = {
        'id': retailer_id,
        'title': product.title,
        'description': product.description or product.title,
        'availability': 'in stock' if product.stock > 0 else 'out of stock',
        'condition': 'new',
        'price': f"{float(product.price):.2f} INR",
        'image_link': image_url,
        'link': image_url,
        'brand': product.business.business_name if hasattr(product.business, 'business_name') else 'E-Com Orbit',
    }

    payload_requests = [
        {
            'method': 'CREATE',
            'data': item_data,
        }
    ]

    import json
    response = requests.post(
        url,
        headers=headers,
        data={
            'item_type': 'PRODUCT_ITEM',
            'requests': json.dumps(payload_requests),
        }
    )

    if response.status_code == 200:
        return {'success': True, 'retailer_id': retailer_id, 'response': response.json()}
    else:
        return {'success': False, 'status_code': response.status_code, 'error': response.text}