import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

WAMA_URL = 'https://api.wa-ma.org/send-message'


def send_whatsapp(phone: str, message: str) -> bool:
    """Send a WhatsApp message via wa-ma.org. Returns True on success."""
    if not settings.WAMA_API_KEY:
        logger.warning('WAMA_API_KEY not set — skipping WhatsApp send to %s', phone)
        return False
    try:
        resp = requests.post(
            WAMA_URL,
            json={'phone_to': phone, 'message': message},
            headers={'Authorization': settings.WAMA_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.error('WhatsApp send failed to %s: %s', phone, exc)
        return False
