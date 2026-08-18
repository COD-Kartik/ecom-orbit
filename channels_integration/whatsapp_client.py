import requests
import json
from django.conf import settings


def _get_credentials(channel):
    """Pulls this specific channel's own WhatsApp credentials, stored at
    connect-time in api_credentials. Returns (phone_number_id, access_token,
    catalog_id) — any of these may be None if not yet configured."""
    creds = channel.api_credentials or {}
    return creds.get('phone_number_id'), creds.get('access_token'), creds.get('catalog_id')


def send_whatsapp_test_message(channel, recipient_number):
    """
    Sends Meta's pre-approved 'hello_world' template message using this
    channel's own credentials, to verify the connection works end-to-end.
    recipient_number must be in international format, no '+', no spaces.
    """
    phone_number_id, access_token, _ = _get_credentials(channel)
    if not phone_number_id or not access_token:
        return {'success': False, 'error': 'This channel is missing WhatsApp credentials. Add them first.'}

    url = f"{settings.WHATSAPP_API_BASE_URL}/{phone_number_id}/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': recipient_number,
        'type': 'template',
        'template': {'name': 'hello_world', 'language': {'code': 'en_US'}},
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        message_id = data.get('messages', [{}])[0].get('id')
        return {'success': True, 'message_id': message_id, 'response': data}
    else:
        return {'success': False, 'status_code': response.status_code, 'error': response.text}


def check_whatsapp_connection(channel):
    """
    Verifies this channel's own credentials are valid with zero side effects —
    a GET request to fetch its phone number's metadata.
    """
    phone_number_id, access_token, _ = _get_credentials(channel)
    if not phone_number_id or not access_token:
        return {'success': False, 'error': 'This channel is missing WhatsApp credentials. Add them first.'}

    url = f"{settings.WHATSAPP_API_BASE_URL}/{phone_number_id}"
    headers = {'Authorization': f'Bearer {access_token}'}

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


import time


import logging
logger = logging.getLogger(__name__)


def sync_product_to_whatsapp(product, channel, method='CREATE'):
    """
    Creates, updates, or deletes a product (and its variants, if any) in
    THIS SPECIFIC CHANNEL's Meta Commerce Catalog.

    items_batch is ASYNCHRONOUS — a 200 response only means Meta accepted
    and queued the request, not that it succeeded. We capture the returned
    handle and poll check_batch_request_status to confirm real completion
    before reporting success.
    """
    phone_number_id, access_token, catalog_id = _get_credentials(channel)
    if not access_token or not catalog_id:
        return {'success': False, 'error': 'This channel is missing WhatsApp credentials. Add them first.'}

    url = f"{settings.WHATSAPP_API_BASE_URL}/{catalog_id}/items_batch"
    headers = {'Authorization': f'Bearer {access_token}'}
    base_retailer_id = f"ECOMORBIT-{product.id}"

    if not product.image and method != 'DELETE':
        return {'success': False, 'status_code': None, 'error': 'Product has no image — WhatsApp catalog requires an image.'}

    gallery_urls = [img.image.url for img in product.extra_images.all()] if method != 'DELETE' else []

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
            item_data = {
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
            if gallery_urls:
                item_data['additional_image_urls'] = gallery_urls
            payload_requests.append({'method': method, 'data': item_data})
    else:
        item_data = {
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
        if gallery_urls:
            item_data['additional_image_urls'] = gallery_urls
        payload_requests.append({'method': method, 'data': item_data})

    response = requests.post(
        url,
        headers=headers,
        data={'item_type': 'PRODUCT_ITEM', 'requests': json.dumps(payload_requests)}
    )

    if response.status_code != 200:
        return {'success': False, 'status_code': response.status_code, 'error': response.text}

    handles = response.json().get('handles')
    handle = handles[0] if handles else None
    if not handle:
        return {'success': False, 'error': 'No batch handle returned — cannot verify processing.'}

    # Poll for real completion — up to ~6 seconds
    status_url = f"{settings.WHATSAPP_API_BASE_URL}/{catalog_id}/check_batch_request_status"
    last_status_response_text = None
    last_status_data = None

    for _ in range(8):
        time.sleep(1.5)
        status_response = requests.get(status_url, headers=headers, params={'handle': handle})
        if status_response.status_code != 200:
            last_status_response_text = f"HTTP {status_response.status_code}: {status_response.text}"
            logger.warning(f"check_batch_request_status HTTP error {status_response.status_code}: {status_response.text}")
            continue
        
        last_status_response_text = status_response.text
        try:
            status_data = status_response.json()
            last_status_data = status_data
        except Exception as e:
            logger.warning(f"check_batch_request_status JSON parse error: {e}. Raw response: {status_response.text}")
            continue

        handles_data = status_data.get('data', status_data.get('handles', []))
        if isinstance(handles_data, dict):
            handles_data = [handles_data]
        elif not isinstance(handles_data, list) and isinstance(status_data, dict) and 'status' in status_data:
            handles_data = [status_data]

        if isinstance(handles_data, list) and handles_data:
            entry = handles_data[0]
            errors = entry.get('errors') or []
            state = entry.get('status', '')
            if state and state.lower() in ('finished', 'completed', 'succeeded'):
                if errors:
                    return {'success': False, 'error': f"Batch completed with errors: {errors}", 'response': status_data}
                if variants and method != 'DELETE':
                    for v, req in zip(variants, payload_requests):
                        v.external_id = req['data']['id']
                        v.save(update_fields=['external_id'])
                return {'success': True, 'retailer_id': base_retailer_id, 'response': status_data}
            if state and state.lower() == 'failed':
                return {'success': False, 'error': f"Batch failed: {status_data}", 'response': status_data}
            # else still in progress — loop again
        else:
            logger.warning(f"check_batch_request_status response missing expected 'data' or 'handles' keys. Raw response: {status_response.text}")

    logger.warning(f"Batch polling completed without final status. Last raw response: {last_status_response_text}")
    if last_status_data and ('data' in last_status_data or 'handles' in last_status_data):
        return {'success': False, 'error': f"Batch still processing after polling — check Commerce Manager manually before assuming success. Last status: {last_status_data}"}
    elif last_status_response_text:
        return {'success': False, 'error': f"Batch status check returned unexpected response format. Raw response: {last_status_response_text}"}
    else:
        return {'success': False, 'error': 'Batch still processing after polling — check Commerce Manager manually before assuming success.'}

def send_order_status_notification(channel, order, status):
    """
    Sends an order status update to the customer via WhatsApp using this
    channel's own credentials and a pre-approved message template.
    """
    phone_number_id, access_token, _ = _get_credentials(channel)
    if not phone_number_id or not access_token:
        return {'success': False, 'error': 'This channel is missing WhatsApp credentials.'}
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

    url = f"{settings.WHATSAPP_API_BASE_URL}/{phone_number_id}/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': order.customer_phone,
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': 'en_US'},
            'components': [{'type': 'body', 'parameters': [{'type': 'text', 'text': str(order.id)}]}]
        },
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        message_id = data.get('messages', [{}])[0].get('id')
        return {'success': True, 'message_id': message_id}
    else:
        return {'success': False, 'status_code': response.status_code, 'error': response.text}