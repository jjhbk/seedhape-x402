"""Fires Seedhape's order.verified webhook with HMAC signature."""

import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request

WEBHOOK_URL = os.environ["SEEDHAPE_WEBHOOK_URL"]
WEBHOOK_SECRET = os.environ["SEEDHAPE_WEBHOOK_SECRET"]


def sign(raw_body: bytes) -> str:
    return "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()


def fire(event_payload: dict) -> bool:
    raw = json.dumps(event_payload, separators=(",", ":")).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Seedhape-Signature": sign(raw),
        "X-Seedhape-Event": event_payload.get("event", "order.verified"),
    }
    req = urllib.request.Request(WEBHOOK_URL, data=raw, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as exc:
        print(f"Webhook delivery failed: {exc.code} {exc.read().decode()}")
        return False
    except Exception as exc:
        print(f"Webhook delivery exception: {exc}")
        return False
