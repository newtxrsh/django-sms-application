"""textbee.dev SMS gateway integration.

All communication with textbee happens here, not in the views. Every public
function returns an SMSResult instead of raising, so the views only need to
check `result.success` and show `result.error` to the user.

Security: the API key is only ever placed in the request header. It is never
logged, stored, or included in error messages shown to the user.
"""

import logging
from dataclasses import dataclass

import requests
from django.conf import settings

from .models import SMSMessage

logger = logging.getLogger(__name__)

TEXTBEE_BASE_URL = 'https://api.textbee.dev/api/v1'
REQUEST_TIMEOUT = 15  # seconds

KNOWN_STATUSES = {
    SMSMessage.Status.PENDING,
    SMSMessage.Status.DISPATCHED,
    SMSMessage.Status.SENT,
    SMSMessage.Status.DELIVERED,
    SMSMessage.Status.FAILED,
}


@dataclass
class SMSResult:
    success: bool
    message_id: str = ''  # textbee smsBatchId
    status: str = ''
    error: str = ''       # user-friendly text, safe to display


class TextbeeError(Exception):
    """A failed textbee request; the message is safe to show to the user."""


def _missing_credentials():
    """Return a user-friendly error if the API key or device ID is not set."""
    if not settings.TEXTBEE_API_KEY or not settings.TEXTBEE_DEVICE_ID:
        logger.error('textbee is not configured: TEXTBEE_API_KEY or TEXTBEE_DEVICE_ID is empty.')
        return ('The SMS service is not configured. '
                'Set TEXTBEE_API_KEY and TEXTBEE_DEVICE_ID in the .env file and restart the server.')
    return ''


def _provider_error_text(body):
    """Extract textbee's error text, which may be in "message" or "error"."""
    if not isinstance(body, dict):
        return ''
    text = body.get('message') or body.get('error') or ''
    if isinstance(text, list):  # validation errors can come back as a list
        text = '; '.join(str(item) for item in text)
    return str(text)[:200]


def _call_textbee(method, path, payload=None):
    """Send a request to textbee and return the parsed JSON body.

    Raises TextbeeError with a user-friendly message on any failure.
    """
    url = f'{TEXTBEE_BASE_URL}{path}'
    headers = {
        'x-api-key': settings.TEXTBEE_API_KEY,
        'Content-Type': 'application/json',
    }
    try:
        if method == 'POST':
            response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        else:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    # Timeout is checked first: a connect timeout is both a Timeout and a ConnectionError.
    except requests.Timeout:
        logger.error('textbee %s %s timed out after %ss.', method, path, REQUEST_TIMEOUT)
        raise TextbeeError('textbee did not respond in time. '
                           'Check your internet connection and try again.')
    except requests.ConnectionError:
        logger.error('Could not connect to textbee for %s %s.', method, path)
        raise TextbeeError('Could not connect to textbee. '
                           'Check your internet connection and try again.')
    except requests.RequestException as exc:
        logger.error('textbee %s %s failed: %s', method, path, type(exc).__name__)
        raise TextbeeError('A network error occurred while contacting textbee. Please try again.')

    try:
        body = response.json()
    except ValueError:
        body = None

    code = response.status_code
    if 200 <= code < 300 and isinstance(body, dict):
        return body

    provider_text = _provider_error_text(body)
    logger.warning('textbee %s %s failed: HTTP %s %s', method, path, code, provider_text)

    if code == 401:
        raise TextbeeError('textbee rejected the API key. '
                           'Check TEXTBEE_API_KEY in the .env file.')
    if code == 400:
        detail = f' ({provider_text})' if provider_text else ''
        raise TextbeeError(f'textbee could not process the request{detail}. '
                           'Make sure the textbee app is running on the phone, the device is '
                           'enabled, and your textbee account email is verified.')
    if code == 429:
        raise TextbeeError('The textbee plan limit has been reached '
                           '(free plan: 50 messages per day, 300 per month).')
    if 200 <= code < 300:
        raise TextbeeError(f'textbee returned an unexpected response (HTTP {code}). Please try again.')
    raise TextbeeError(f'The SMS provider returned an error (HTTP {code}). Please try again later.')


def send_sms(recipient, message):
    """Submit an SMS to textbee.

    A success result means textbee ACCEPTED the message (status "pending"),
    not that it was delivered.
    """
    error = _missing_credentials()
    if error:
        return SMSResult(success=False, status=SMSMessage.Status.NOT_SUBMITTED, error=error)

    payload = {
        'recipients': [recipient],
        'message': message,
        'deviceId': settings.TEXTBEE_DEVICE_ID,
    }
    try:
        body = _call_textbee('POST', '/gateway/send-sms', payload)
    except TextbeeError as exc:
        return SMSResult(success=False, status=SMSMessage.Status.NOT_SUBMITTED, error=str(exc))

    data = body.get('data', body)
    batch_id = data.get('smsBatchId') if isinstance(data, dict) else None
    if not batch_id or data.get('success') is False:
        logger.warning('textbee accepted the request but returned no smsBatchId.')
        return SMSResult(success=False, status=SMSMessage.Status.NOT_SUBMITTED,
                         error='textbee did not accept the message. Please try again.')

    logger.info('SMS submitted to textbee, batch %s.', batch_id)
    return SMSResult(success=True, message_id=str(batch_id), status=SMSMessage.Status.PENDING)


def get_sms_status(batch_id):
    """Fetch the latest status of a submitted message from textbee."""
    error = _missing_credentials()
    if error:
        return SMSResult(success=False, message_id=batch_id, error=error)

    path = f'/gateway/devices/{settings.TEXTBEE_DEVICE_ID}/sms-batch/{batch_id}'
    try:
        body = _call_textbee('GET', path)
    except TextbeeError as exc:
        return SMSResult(success=False, message_id=batch_id, error=str(exc))

    data = body.get('data', body)
    messages = data.get('messages') if isinstance(data, dict) else None
    first = messages[0] if isinstance(messages, list) and messages else None
    status = str(first.get('status', '')).lower() if isinstance(first, dict) else ''

    if status not in KNOWN_STATUSES:
        logger.warning('textbee returned an unrecognised status for batch %s: %r', batch_id, status)
        return SMSResult(success=False, message_id=batch_id,
                         error='textbee did not return a recognised status. Please try again later.')

    return SMSResult(success=True, message_id=batch_id, status=status)
