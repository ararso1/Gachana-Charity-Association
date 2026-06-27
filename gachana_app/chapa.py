import hashlib
import hmac
import json

import requests
from django.conf import settings


class ChapaError(Exception):
    pass


def initialize_payment(
    *,
    amount,
    email,
    first_name,
    last_name,
    phone_number,
    tx_ref,
    callback_url,
    return_url,
    description='Charity donation',
):
    """Initialize a Chapa checkout session."""
    secret = settings.CHAPA_SECRET_KEY
    if not secret:
        raise ChapaError('Chapa secret key is not configured.')

    payload = {
        'amount': str(amount),
        'currency': settings.CHAPA_CURRENCY,
        'email': email or 'donor@gachanacharity.com',
        'first_name': first_name or 'Gachana',
        'last_name': last_name or 'Donor',
        'phone_number': phone_number,
        'tx_ref': tx_ref,
        'callback_url': callback_url,
        'return_url': return_url,
        'customization': {
            # Chapa limits the title to 16 characters.
            'title': 'Gachana Charity',
            'description': description,
        },
    }

    response = requests.post(
        f'{settings.CHAPA_BASE_URL}/transaction/initialize',
        json=payload,
        headers={
            'Authorization': f'Bearer {secret}',
            'Content-Type': 'application/json',
        },
        timeout=30,
    )
    data = response.json()
    if response.status_code != 200 or data.get('status') != 'success':
        raise ChapaError(_format_chapa_error(data))

    return data['data']


def _format_chapa_error(data):
    """Turn a Chapa error response into a readable message."""
    message = data.get('message')
    if isinstance(message, dict):
        parts = []
        for field, errors in message.items():
            if isinstance(errors, (list, tuple)):
                parts.append(f"{field}: {', '.join(str(e) for e in errors)}")
            else:
                parts.append(f"{field}: {errors}")
        if parts:
            return 'Payment error — ' + '; '.join(parts)
    if message:
        return str(message)
    return 'Failed to initialize Chapa payment.'


def verify_payment(tx_ref):
    """Verify a Chapa transaction by tx_ref."""
    secret = settings.CHAPA_SECRET_KEY
    if not secret:
        raise ChapaError('Chapa secret key is not configured.')

    response = requests.get(
        f'{settings.CHAPA_BASE_URL}/transaction/verify/{tx_ref}',
        headers={'Authorization': f'Bearer {secret}'},
        timeout=30,
    )
    data = response.json()
    if response.status_code != 200:
        raise ChapaError(data.get('message', 'Failed to verify Chapa payment.'))
    return data


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    secret = settings.CHAPA_WEBHOOK_SECRET or settings.CHAPA_SECRET_KEY
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def parse_webhook_payload(raw_body: bytes):
    return json.loads(raw_body.decode())
