import base64
import json
import os
import time
import uuid

import facilitator_client
import webhook_emitter
from catalog import find_product, list_merchants, list_products

NETWORK_ID = os.environ.get("NETWORK_ID", "base-sepolia")
USDC_ADDRESS = os.environ["USDC_ADDRESS"]
PAYMENT_RECIPIENT = os.environ["PAYMENT_RECIPIENT_ADDRESS"]
INR_PER_USDC = float(os.environ.get("INR_PER_USDC", "84"))


def _build_requirements(merchant, merchant_id, product_id, product, request_url):
    price_usdc = product["price_inr"] / INR_PER_USDC
    max_amount_atomic = str(int(round(price_usdc * 1_000_000)))
    return {
        "scheme": "exact",
        "network": NETWORK_ID,
        "maxAmountRequired": max_amount_atomic,
        "resource": request_url,
        "description": f"{merchant['name']} - {product['name']}",
        "mimeType": "application/json",
        "payTo": PAYMENT_RECIPIENT,
        "maxTimeoutSeconds": 60,
        "asset": USDC_ADDRESS,
        "extra": {
            "name": "USDC",
            "version": "2",
            "merchantId": merchant_id,
            "productId": product_id,
            "merchantName": merchant["name"],
            "productName": product["name"],
            "priceINR": product["price_inr"],
        },
    }


def _resp(status, body, extra_headers=None):
    headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
    if extra_headers:
        headers.update(extra_headers)
    return {"statusCode": status, "headers": headers, "body": json.dumps(body)}


def lambda_handler(event, context):
    raw_path = event.get("rawPath") or event.get("path", "")
    parts = raw_path.strip("/").split("/")
    method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod") or "GET").upper()

    if method != "GET":
        return _resp(405, {"error": "method_not_allowed", "method": method})

    if raw_path == "/merchants":
        return _resp(200, {"merchants": list_merchants()})

    if len(parts) == 3 and parts[0] == "merchants" and parts[2] == "products":
        merchant_id = parts[1]
        products = list_products(merchant_id)
        if products is None:
            return _resp(404, {"error": "merchant_not_found"})
        return _resp(200, {"merchant_id": merchant_id, "products": products})

    if len(parts) != 5 or parts[0] != "merchants" or parts[2] != "products" or parts[4] != "buy":
        return _resp(404, {"error": "not_found", "path": raw_path})

    merchant_id, product_id = parts[1], parts[3]
    merchant, product = find_product(merchant_id, product_id)
    if not merchant or not product:
        return _resp(404, {"error": "product_not_found"})

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    payment_header = headers.get("x-payment")

    domain = event.get("requestContext", {}).get("domainName", "localhost")
    request_url = f"https://{domain}{raw_path}"
    requirements = _build_requirements(merchant, merchant_id, product_id, product, request_url)

    if not payment_header:
        return _resp(
            402,
            {
                "x402Version": 1,
                "accepts": [requirements],
                "error": "X-PAYMENT header required",
            },
        )

    try:
        payment_payload = json.loads(base64.b64decode(payment_header).decode("utf-8"))
    except Exception as exc:
        return _resp(400, {"error": "invalid_x_payment_header", "detail": str(exc)})

    verify_resp = facilitator_client.verify(payment_payload, requirements)
    if not verify_resp.get("isValid"):
        return _resp(402, {"error": "verification_failed", "detail": verify_resp})

    settle_resp = facilitator_client.settle(payment_payload, requirements)
    if not settle_resp.get("success"):
        return _resp(402, {"error": "settlement_failed", "detail": settle_resp})

    tx_hash = settle_resp.get("transaction") or settle_resp.get("txHash")
    payer = settle_resp.get("payer") or payment_payload.get("payload", {}).get(
        "authorization", {}
    ).get("from")

    order_id = f"ord_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    webhook_payload = {
        "event": "order.verified",
        "order_id": order_id,
        "merchant_id": merchant_id,
        "merchant_name": merchant["name"],
        "product_id": product_id,
        "product_name": product["name"],
        "amount_inr": product["price_inr"],
        "amount_usdc_atomic": requirements["maxAmountRequired"],
        "payment_method": "x402",
        "chain": NETWORK_ID,
        "tx_hash": tx_hash,
        "payer_address": payer,
        "timestamp": int(time.time()),
    }
    webhook_ok = webhook_emitter.fire(webhook_payload)

    settle_resp_b64 = base64.b64encode(json.dumps(settle_resp).encode("utf-8")).decode("utf-8")
    return _resp(
        200,
        {
            "order_id": order_id,
            "status": "confirmed",
            "merchant": merchant["name"],
            "merchant_location": merchant["location"],
            "product": product["name"],
            "amount_inr": product["price_inr"],
            "tx_hash": tx_hash,
            "explorer_url": f"https://sepolia.basescan.org/tx/{tx_hash}",
            "delivery_eta_days": 7,
            "webhook_delivered": webhook_ok,
        },
        extra_headers={"X-Payment-Response": settle_resp_b64},
    )
