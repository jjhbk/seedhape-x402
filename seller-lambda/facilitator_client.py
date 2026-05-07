"""Talks to the CDP x402 facilitator."""

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

from cdp.auth.utils.jwt import JwtOptions, generate_jwt

FACILITATOR_URL = os.environ["FACILITATOR_URL"]
CDP_API_KEY_ID = os.environ.get("CDP_API_KEY_ID", "")
CDP_API_KEY_SECRET = os.environ.get("CDP_API_KEY_SECRET", "")


def _auth_headers(path: str) -> dict:
    if not CDP_API_KEY_ID or not CDP_API_KEY_SECRET:
        return {}
    parsed = urlparse(FACILITATOR_URL)
    host = parsed.netloc
    if host != "api.cdp.coinbase.com":
        return {}
    base_path = parsed.path.rstrip("/")
    request_path = f"{base_path}{path}"

    # CDP facilitator requires bearer JWT signed from API key secret.
    token = generate_jwt(
        JwtOptions(
            api_key_id=CDP_API_KEY_ID,
            api_key_secret=CDP_API_KEY_SECRET,
            request_method="POST",
            request_host=host,
            request_path=request_path,
            expires_in=120,
        )
    )
    return {"Authorization": f"Bearer {token}"}


def _post(path: str, body: dict) -> dict:
    url = FACILITATOR_URL.rstrip("/") + path
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", **_auth_headers(path)}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "error": True,
            "status": exc.code,
            "body": exc.read().decode("utf-8", errors="replace"),
        }
    except Exception as exc:
        return {"error": True, "status": 500, "body": str(exc)}


def verify(payment_payload: dict, payment_requirements: dict) -> dict:
    return _post(
        "/verify",
        {
            "x402Version": 1,
            "paymentPayload": payment_payload,
            "paymentRequirements": payment_requirements,
        },
    )


def settle(payment_payload: dict, payment_requirements: dict) -> dict:
    return _post(
        "/settle",
        {
            "x402Version": 1,
            "paymentPayload": payment_payload,
            "paymentRequirements": payment_requirements,
        },
    )
