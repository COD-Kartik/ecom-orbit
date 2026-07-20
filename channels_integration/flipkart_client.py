import requests
from django.conf import settings


def get_flipkart_access_token():
    """
    Requests a fresh access token from Flipkart's sandbox using the
    Client Credentials flow — authenticates as our own app, not on
    behalf of another seller (since we're using a Self Access Application).
    """
    url = f"{settings.FLIPKART_SANDBOX_BASE_URL}/oauth-service/oauth/token"

    params = {
        'grant_type': 'client_credentials',
        'scope': 'Seller_Api',
    }

    response = requests.post(
        url,
        params=params,
        auth=(settings.FLIPKART_API_KEY, settings.FLIPKART_API_SECRET),
    )

    if response.status_code == 200:
        data = response.json()
        return {
            'success': True,
            'access_token': data.get('access_token'),
            'expires_in': data.get('expires_in'),
        }
    else:
        return {
            'success': False,
            'status_code': response.status_code,
            'error': response.text,
        }
    
def push_product_to_flipkart(access_token, product):
    """
    Creates or updates a product listing on Flipkart using their Listings API.
    Maps our internal Product model to Flipkart's expected listing format.
    """
    url = f"{settings.FLIPKART_SANDBOX_BASE_URL}/sellers/listings/v3/create"

    sku_id = f"ECOMORBIT-{product.id}"

    payload = {
        "requests": [
            {
                "sku_id": sku_id,
                "product_data": {
                    "title": product.title,
                    "description": product.description or "",
                },
                "pricing": {
                    "mrp": float(product.price),
                    "selling_price": float(product.price),
                },
                "inventory": {
                    "stock": product.stock,
                },
            }
        ]
    }

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return {'success': True, 'sku_id': sku_id, 'response': response.json()}
    else:
        return {'success': False, 'status_code': response.status_code, 'error': response.text}
    
def fetch_flipkart_orders(access_token, page_size=20):
    """
    Retrieves orders from Flipkart's Order Search API.
    Uses POST with a filter body, matching Flipkart's documented pattern
    (same style as their Shipments Search API).
    """
    url = f"{settings.FLIPKART_SANDBOX_BASE_URL}/sellers/v3/orders/search"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    payload = {
        'filter': {
            'states': ['APPROVED'],
            'pageSize': page_size,
        }
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return {'success': True, 'data': response.json()}
    else:
        return {'success': False, 'status_code': response.status_code, 'error': response.text}