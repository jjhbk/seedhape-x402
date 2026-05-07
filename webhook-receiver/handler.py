import base64
import hashlib
import hmac
import json
import os

WEBHOOK_SECRET = os.environ["SEEDHAPE_WEBHOOK_SECRET"]


def _verify(raw_body: bytes, signature: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[7:])


def lambda_handler(event, context):
    raw = (event.get("body") or "").encode("utf-8")
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(event["body"])

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    sig = headers.get("x-seedhape-signature", "")
    if not _verify(raw, sig):
        print(f"Invalid signature. Got: {sig}")
        return {"statusCode": 401, "body": "invalid signature"}

    payload = json.loads(raw)
    print("Verified order.verified webhook")
    print(json.dumps(payload, indent=2))

    inr = payload["amount_inr"]
    merchant = payload["merchant_name"]
    product = payload["product_name"]
    tx = payload["tx_hash"]
    msg = (
        f"[WhatsApp -> {merchant}]\\n"
        f"New order received: {product}\\n"
        f"Amount: INR {inr} (settled via x402 on Base)\\n"
        f"Tx: https://sepolia.basescan.org/tx/{tx}\\n"
        f"Order ID: {payload['order_id']}"
    )
    print(msg)
    return {
        "statusCode": 200,
        "body": json.dumps({"received": True, "whatsapp_simulated": msg}),
    }
