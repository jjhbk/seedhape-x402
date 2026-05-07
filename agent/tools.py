"""Tool functions exposed to the agent's LLM."""

import json
import os
import urllib.request

from x402_client import fetch_with_payment

SELLER_API_BASE = os.environ["SELLER_API_BASE"].rstrip("/")

def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def discover_merchants(category: str | None = None, region: str | None = None) -> list:
    payload = _http_get_json(f"{SELLER_API_BASE}/merchants")
    out = payload.get("merchants", [])
    if category:
        out = [m for m in out if category.lower() in m["category"].lower()]
    if region:
        out = [
            m
            for m in out
            if region.lower() in m.get("region", "").lower()
            or region.lower() in m.get("location", "").lower()
        ]
    return out


def browse_storefront(merchant_id: str) -> list:
    payload = _http_get_json(f"{SELLER_API_BASE}/merchants/{merchant_id}/products")
    return payload.get("products", [])


def place_order(merchant_id: str, product_id: str) -> dict:
    url = f"{SELLER_API_BASE}/merchants/{merchant_id}/products/{product_id}/buy"
    return fetch_with_payment(url)
