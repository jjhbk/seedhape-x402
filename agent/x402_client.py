"""x402 client: handles 402 challenge and retry with signed payment."""

import base64
import json
import os
import time
import urllib.error
import urllib.request

from eth_account import Account

AGENT_PRIVATE_KEY = os.environ.get("AGENT_PRIVATE_KEY", "")


class X402Error(RuntimeError):
    pass


def _http_get(url: str, headers: dict | None = None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def _build_fallback_payload(requirements: dict) -> str:
    if not AGENT_PRIVATE_KEY:
        raise X402Error(
            "AGENT_PRIVATE_KEY is required for fallback signing when x402 package is unavailable"
        )

    acct = Account.from_key(AGENT_PRIVATE_KEY)
    now = int(time.time())
    auth = {
        "from": acct.address,
        "to": requirements["payTo"],
        "value": requirements["maxAmountRequired"],
        "validAfter": str(now - 10),
        "validBefore": str(now + 60),
        "nonce": "0x" + os.urandom(32).hex(),
    }

    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "domain": {
            "name": requirements.get("extra", {}).get("name", "USDC"),
            "version": requirements.get("extra", {}).get("version", "2"),
            "chainId": 84532,
            "verifyingContract": requirements["asset"],
        },
        "primaryType": "TransferWithAuthorization",
        "message": auth,
    }

    sig = Account.sign_typed_data(acct.key, full_message=typed_data).signature.hex()
    if not sig.startswith("0x"):
        sig = f"0x{sig}"
    payload = {
        "x402Version": 1,
        "scheme": "exact",
        "network": requirements["network"],
        "payload": {"signature": sig, "authorization": auth},
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def fetch_with_payment(url: str) -> dict:
    status, _, body = _http_get(url)
    if status == 200:
        return json.loads(body)
    if status != 402:
        raise X402Error(f"Unexpected status {status}: {body[:200]}")

    challenge = json.loads(body)
    requirements = challenge["accepts"][0]
    x_payment = _build_fallback_payload(requirements)

    status2, _, body2 = _http_get(url, headers={"X-PAYMENT": x_payment})
    if status2 != 200:
        raise X402Error(f"Payment retry failed {status2}: {body2[:500]}")
    return json.loads(body2)
