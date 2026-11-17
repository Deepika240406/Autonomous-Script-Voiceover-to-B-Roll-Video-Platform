import hmac
import hashlib
import json
import httpx
from app.core.logging import logger
from app.core.security import is_safe_url
from app.config import settings


async def dispatch_callback(callback_url: str, payload: dict, secret: str = settings.HMAC_SECRET) -> bool:
    """
    Sends job completion/status webhook to callback_url signed with HMAC-SHA256
    in the X-IncuBrix-Signature header.
    Validates URL against SSRF before sending.
    """
    try:
        # Validate SSRF
        is_safe_url(callback_url, allow_local_for_dev=settings.DEBUG or settings.ENVIRONMENT == "development")

        body_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-IncuBrix-Signature": signature,
            "User-Agent": f"IncuBrix-Webhook-Dispatcher/{settings.APP_VERSION}",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(callback_url, content=body_bytes, headers=headers)
            logger.info(f"Callback dispatched to {callback_url}, response status: {resp.status_code}")
            return resp.status_code < 400
    except Exception as e:
        logger.error(f"Failed to dispatch callback to {callback_url}: {str(e)}")
        return False
