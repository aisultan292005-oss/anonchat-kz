"""
SMS verification via Mobizon (Kazakhstan local provider).
Docs: https://mobizon.kz/help/api-docs
"""
import asyncio
import logging
import random
import aiohttp

logger = logging.getLogger(__name__)

# In-memory code storage: {user_id: {"code": str, "phone": str, "attempts": int}}
_pending: dict[int, dict] = {}
MAX_ATTEMPTS = 3


def generate_code() -> str:
    return str(random.randint(100000, 999999))


async def send_sms(phone: str, code: str, api_key: str) -> bool:
    """Send SMS via Mobizon API."""
    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone.startswith("+"):
        phone = "+" + phone

    url = "https://api.mobizon.kz/service/message/sendsmsmessage"
    params = {
        "apiKey": api_key,
        "recipient": phone,
        "text": f"AnonChat KZ — ваш код подтверждения: {code}. Никому не сообщайте.",
        "output": "json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                if data.get("code") == 0:
                    logger.info("SMS sent to %s", phone)
                    return True
                else:
                    logger.error("Mobizon error: %s", data)
                    return False
    except Exception as e:
        logger.error("SMS send failed: %s", e)
        return False


def store_code(user_id: int, phone: str, code: str) -> None:
    _pending[user_id] = {"code": code, "phone": phone, "attempts": 0}


def verify_code(user_id: int, entered: str) -> str:
    """Returns: 'ok' | 'wrong' | 'expired' | 'blocked'"""
    data = _pending.get(user_id)
    if not data:
        return "expired"
    if data["attempts"] >= MAX_ATTEMPTS:
        return "blocked"
    if data["code"] == entered.strip():
        _pending.pop(user_id, None)
        return "ok"
    data["attempts"] += 1
    return "wrong"


def get_phone(user_id: int) -> str | None:
    data = _pending.get(user_id)
    return data["phone"] if data else None


def clear(user_id: int) -> None:
    _pending.pop(user_id, None)
