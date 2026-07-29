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
    


def sync_product_to_whatsapp(product, method='CREATE'):
    """
    Creates, updates, or deletes a product (and its variants, if any) in the
    Meta Commerce Catalog via items_batch. method: 'CREATE', 'UPDATE', or 'DELETE'.

    If the product has variants, each variant becomes its own catalog item
    (retailer_id like ECOMORBIT-8-V3), grouped under item_group_id ECOMORBIT-8
    so customers can select and order variants independently. If no variants
    exist, the product itself is synced as a single item.

    Uses product.image.url directly — Cloudinary storage already returns a
    full public HTTPS URL, so no base_url needs to be prepended.
    """
    url = f"{settings.WHATSAPP_API_BASE_URL}/{settings.WHATSAPP_CATALOG_ID}/items_batch"
    headers = {'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}'}
    base_retailer_id = f"ECOMORBIT-{product.id}"

    if not product.image and method != 'DELETE':
        return {'success': False, 'status_code': None, 'error': 'Product has no image — WhatsApp catalog requires an image.'}

    payload_requests = []
    variants = list(product.variants.all())

    if method == 'DELETE':
        payload_requests.append({'method': 'DELETE', 'data': {'id': base_retailer_id}})
        for v in variants:
            variant_retailer_id = v.external_id or f"{base_retailer_id}-V{v.id}"
            payload_requests.append({'method': 'DELETE', 'data': {'id': variant_retailer_id}})
    elif variants:
        for v in variants:
            variant_retailer_id = f"{base_retailer_id}-V{v.id}"
            payload_requests.append({
                'method': method,
                'data': {
                    'id': variant_retailer_id,
                    'item_group_id': base_retailer_id,
                    'title': f"{product.title} - {v.name}",
                    'description': product.description or product.title,
                    'availability': 'in stock' if v.stock > 0 else 'out of stock',
                    'condition': 'new',
                    'price': f"{float(v.price):.2f} INR",
                    'image_link': product.image.url,
                    'link': product.image.url,
                    'brand': product.business.business_name if hasattr(product.business, 'business_name') else 'E-Com Orbit',
                }
            })
    else:
        payload_requests.append({
            'method': method,
            'data': {
                'id': base_retailer_id,
                'title': product.title,
                'description': product.description or product.title,
                'availability': 'in stock' if product.stock > 0 else 'out of stock',
                'condition': 'new',
                'price': f"{float(product.price):.2f} INR",
                'image_link': product.image.url,
                'link': product.image.url,
                'brand': product.business.business_name if hasattr(product.business, 'business_name') else 'E-Com Orbit',
            }
        })

    import json
    response = requests.post(
        url,
        headers=headers,
        data={'item_type': 'PRODUCT_ITEM', 'requests': json.dumps(payload_requests)}
    )

    if response.status_code == 200:
        if variants and method != 'DELETE':
            for v, req in zip(variants, payload_requests):
                v.external_id = req['data']['id']
                v.save(update_fields=['external_id'])
        return {'success': True, 'retailer_id': base_retailer_id, 'response': response.json()}
    else:
        return {'success': False, 'status_code': response.status_code, 'error': response.text}


    
def send_order_status_notification(order, status):
    """
    Sends an order status update to the customer via WhatsApp using a
    pre-approved message template. Templates (order_shipped, order_delivered,
    order_cancelled) must exist and be approved in Meta Business Suite's
    Message Templates section before this works — until then, this fails
    gracefully with a clear error rather than raising.
    """
    if not order.customer_phone:
        return {'success': False, 'error': 'No customer phone number on order.'}

    template_map = {
        'shipped': 'order_shipped',
        'delivered': 'order_delivered',
        'cancelled': 'order_cancelled',
    }
    template_name = template_map.get(status)
    if not template_name:
        return {'success': False, 'error': f'No template configured for status "{status}".'}

    url = f"{settings.WHATSAPP_API_BASE_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
        'Content-Type': 'application/json',
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': order.customer_phone,
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': 'en_US'},
            'components': [
                {
                    'type': 'body',
                    'parameters': [
                        {'type': 'text', 'text': str(order.id)},
                    ]
                }
            ]
        },
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        message_id = data.get('messages', [{}])[0].get('id')
        return {'success': True, 'message_id': message_id}
    else:
        return {'success': False, 'status_code': response.status_code, 'error': response.text}

    