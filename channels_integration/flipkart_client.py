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