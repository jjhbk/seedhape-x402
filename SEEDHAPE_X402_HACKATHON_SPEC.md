# Seedhape × x402 — Hackathon MVP Spec (3–4 hours)

> **For Claude Code.** Read this entire document before writing any code. Then execute phase-by-phase. If a phase blows past its time budget by more than 10 minutes, drop the optional items and move on. Speed > completeness.

---

## 0. Mission — the one-paragraph pitch

Every other x402 demo is an agent paying $0.01 to scrape an article. **We're connecting the agentic economy to real-world physical commerce in emerging markets.** Seedhape is a UPI-based payment gateway powering Rasphia (a WhatsApp-onboarded storefront platform for small Indian merchants). By bolting x402 onto Seedhape, an autonomous agent in NYC can place a wholesale order with a merchant in Jaipur, settle in USDC on Base in ~5 seconds, and the merchant gets a WhatsApp notification in ₹INR — never sees crypto, no wallet, no friction. **We just made 60M+ Indian merchants reachable by every agent on the x402 Bazaar.**

---

## 1. What you're building (90-second tour)

```
[Local Python agent: Strands + Coinbase AgentKit + Anthropic Claude]
                            │
                            │ HTTP GET /merchants/{id}/products/{id}/buy
                            ▼
              ┌─────────────────────────────────────┐
              │  AWS API Gateway → AWS Lambda       │   ◄─── This is the seller
              │  (Python, x402-compliant endpoint)   │
              └──────┬──────────────────┬───────────┘
                     │                  │
        ┌────────────▼─┐      ┌─────────▼──────────┐
        │ CDP x402     │      │ Seedhape webhook   │
        │ Facilitator  │      │ receiver (Lambda)  │
        │ verify+settle│      │ Logs order.verified│
        │ on Base      │      │ Mocks WhatsApp ping│
        │ Sepolia      │      │                    │
        └──────────────┘      └────────────────────┘
                     │
                     ▼
              Base Sepolia (USDC settles, tx hash on basescan)
```

**Three deployables, one demo.**

1. `seller-lambda/` — the x402-enabled merchant endpoint (the unique angle)
2. `agent/` — the autonomous buyer (uses AWS reference patterns)
3. `webhook-receiver/` — the mock Seedhape side (proves the bridge)
4. `demo-ui/` (optional, if time) — single HTML page showing the flow live

**Repo layout:**

```
seedhape-x402-mvp/
├── README.md                    # Pitch + run instructions (Phase 5)
├── seller-lambda/
│   ├── handler.py
│   ├── catalog.py
│   ├── facilitator_client.py
│   ├── webhook_emitter.py
│   ├── requirements.txt
│   └── template.yaml            # AWS SAM
├── webhook-receiver/
│   ├── handler.py
│   ├── requirements.txt
│   └── template.yaml            # AWS SAM (or fold into seller stack)
├── agent/
│   ├── buy.py                   # Main agent loop
│   ├── tools.py                 # discover_merchants / browse / place_order
│   ├── x402_client.py           # 402 → sign → retry helper
│   ├── requirements.txt
│   └── .env.example
├── demo-ui/
│   └── index.html               # Optional, Phase 4
└── docs/
    └── architecture.md          # Diagram + judging criteria mapping
```

---

## 2. Hard rules — don't get nerd-sniped

These are the things that will eat your time. Refuse them.

- **DO NOT use CloudFront + Lambda@Edge.** Lambda@Edge propagation is 5–30 min per change. We have hours, not days. Use API Gateway + regular Lambda. Tell judges: *"Production architecture moves to CloudFront + Lambda@Edge for global edge latency — payment logic is identical."*
- **DO NOT deploy to AgentCore Runtime.** Cold start setup + region restrictions will burn 60+ minutes. Run the agent locally. Frame as: *"AgentCore-ready — runs locally for hackathon iteration speed."*
- **DO NOT use Base mainnet.** Base Sepolia testnet only. Free USDC from faucet. One env var (`NETWORK_ID`) to flip later.
- **DO NOT add a real database.** In-memory Python dict for the catalog. DynamoDB is a 30-minute distraction.
- **DO NOT add auth, rate limiting, observability.** Public Lambda URL. CloudWatch logs only. No WAF.
- **DO NOT integrate the actual Rasphia/Seedhape codebase.** Mock the webhook receiver. The bridge is what wins, not the prod integration.
- **DO NOT write tests.** Hackathon. Manual smoke tests via curl + the agent run.
- **DO NOT add an off-ramp / forex provider.** Hardcode `1 USDC = 84 INR`. Mention "post-hackathon: USDC→INR via partner" in README.

---

## 3. Pre-flight (15 min, do this first)

### 3.1 Accounts you need
- [ ] **AWS account** with CLI configured. Verify: `aws sts get-caller-identity` returns your identity.
- [ ] **CDP account** at https://portal.cdp.coinbase.com/ — create an API key. Save `CDP_API_KEY_ID`, `CDP_API_KEY_SECRET`, `CDP_WALLET_SECRET`.
- [ ] **Anthropic API key** at https://console.anthropic.com/ — for the agent's LLM brain. Save `ANTHROPIC_API_KEY`.
- [ ] **Base Sepolia ETH faucet** — for gas. Use https://www.alchemy.com/faucets/base-sepolia or https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet.
- [ ] **Base Sepolia USDC faucet** — https://faucet.circle.com/ — pick Base Sepolia, request USDC. Need at least 5 USDC.

### 3.2 Wallet setup
- [ ] Create a CDP-managed wallet via the CDP SDK. This will be the agent's wallet (the payer).
- [ ] Note its EVM address. Send ~0.01 Base Sepolia ETH and ~5 USDC to it from the faucets.
- [ ] Create a second EVM address (any Coinbase/MetaMask wallet works) — this is the **Seedhape treasury** that receives payments. Save its address as `PAYMENT_RECIPIENT_ADDRESS`. Doesn't need funding.

### 3.3 Tools to install locally
```bash
# AWS SAM CLI for fast Lambda deploys
brew install aws-sam-cli   # or pipx install aws-sam-cli

# Python 3.12+
python3 --version

# Node (only if you need it for any utility scripts)
node --version
```

### 3.4 Reference repos to clone (read-only, for code lifting)
```bash
git clone https://github.com/aws-samples/sample-agentcore-cloudfront-x402-payments ../ref-aws
git clone https://github.com/coinbase/x402 ../ref-x402
git clone https://github.com/coinbase/agentkit ../ref-agentkit
```
You'll lift the agent's x402 client + EIP-3009 signing logic from these. Do not copy wholesale — read, understand, port the minimum needed.

### 3.5 Critical constants to lock in now

```python
# Network: Base Sepolia testnet
NETWORK_ID = "base-sepolia"
USDC_CONTRACT_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
USDC_DECIMALS = 6

# Demo FX peg — DO NOT compute this dynamically for MVP
INR_PER_USDC = 84

# CDP facilitator endpoint — VERIFY in CDP docs at build time, this changes
# Look in https://docs.cdp.coinbase.com/ under x402 / Facilitator
CDP_FACILITATOR_URL = "https://api.cdp.coinbase.com/platform/v2/x402"  # CONFIRM THIS
# Fallback (testnet-only, no auth required): https://x402.org/facilitator
```

> **Claude Code: before Phase 1, fetch the current CDP docs to confirm the facilitator URL and auth scheme.** The hackathon explicitly requires CDP's facilitator. If CDP requires API key auth, plumb it through `Authorization: Bearer ${CDP_API_KEY_ID}:${CDP_API_KEY_SECRET}` or whatever the current docs specify.

---

## 4. Phase 1 — Seller Lambda (60 min) ⭐ critical path

This is the unique part. Everything else is glue. Spend the time here.

### 4.1 Goal
A single AWS Lambda behind API Gateway that:
1. Returns HTTP 402 with x402 payment requirements when no `x-payment` header is present
2. On retry with `x-payment` header: calls CDP facilitator `/verify`, then `/settle`, fires the Seedhape webhook on success, returns 200 with order confirmation

### 4.2 File: `seller-lambda/catalog.py`
```python
"""In-memory catalog. Real Seedhape pulls from merchant DB."""

CATALOG = {
    "jaipur-textiles": {
        "name": "Jaipur Block Print Co",
        "location": "Jaipur, Rajasthan",
        "products": {
            "kurta-indigo-m": {
                "name": "Hand-block-printed cotton kurta — indigo, M",
                "price_inr": 420,
                "stock": 200,
            },
            "kurta-indigo-l": {
                "name": "Hand-block-printed cotton kurta — indigo, L",
                "price_inr": 420,
                "stock": 150,
            },
            "scarf-madder": {
                "name": "Madder-dyed cotton scarf",
                "price_inr": 280,
                "stock": 80,
            },
        },
    },
    "kerala-spices": {
        "name": "Wayanad Spice Collective",
        "location": "Wayanad, Kerala",
        "products": {
            "cardamom-100g": {
                "name": "Single-estate green cardamom, 100g",
                "price_inr": 350,
                "stock": 500,
            },
            "pepper-100g": {
                "name": "Tellicherry black pepper, 100g",
                "price_inr": 180,
                "stock": 1000,
            },
        },
    },
}

def find_product(merchant_id: str, product_id: str):
    m = CATALOG.get(merchant_id)
    if not m:
        return None, None
    p = m["products"].get(product_id)
    if not p:
        return m, None
    return m, p
```

### 4.3 File: `seller-lambda/facilitator_client.py`
```python
"""Talks to the CDP x402 facilitator."""
import json
import os
import urllib.request
import urllib.error

FACILITATOR_URL = os.environ["FACILITATOR_URL"]
CDP_API_KEY_ID = os.environ.get("CDP_API_KEY_ID", "")
CDP_API_KEY_SECRET = os.environ.get("CDP_API_KEY_SECRET", "")

def _post(path: str, body: dict) -> dict:
    url = FACILITATOR_URL.rstrip("/") + path
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    # TODO: confirm CDP auth scheme. If JWT, generate per CDP docs. If basic, use this:
    if CDP_API_KEY_ID and CDP_API_KEY_SECRET:
        # Placeholder — replace with whatever CDP's current auth requires.
        # As of writing, CDP uses JWT signed with the API key secret.
        headers["Authorization"] = f"Bearer {CDP_API_KEY_ID}:{CDP_API_KEY_SECRET}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return {"error": True, "status": e.code, "body": body}

def verify(payment_payload: dict, payment_requirements: dict) -> dict:
    return _post("/verify", {
        "x402Version": 1,
        "paymentPayload": payment_payload,
        "paymentRequirements": payment_requirements,
    })

def settle(payment_payload: dict, payment_requirements: dict) -> dict:
    return _post("/settle", {
        "x402Version": 1,
        "paymentPayload": payment_payload,
        "paymentRequirements": payment_requirements,
    })
```

### 4.4 File: `seller-lambda/webhook_emitter.py`
```python
"""Fires Seedhape's order.verified webhook with HMAC signature (matches existing Seedhape pattern)."""
import hmac
import hashlib
import json
import os
import urllib.request
import urllib.error

WEBHOOK_URL = os.environ["SEEDHAPE_WEBHOOK_URL"]
WEBHOOK_SECRET = os.environ["SEEDHAPE_WEBHOOK_SECRET"]

def sign(raw_body: bytes) -> str:
    return "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
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
    except urllib.error.HTTPError as e:
        print(f"Webhook delivery failed: {e.code} {e.read().decode()}")
        return False
    except Exception as e:
        print(f"Webhook delivery exception: {e}")
        return False
```

### 4.5 File: `seller-lambda/handler.py`

The main handler. The structure:

```python
import base64
import json
import os
import time
import uuid

from catalog import find_product
import facilitator_client
import webhook_emitter

NETWORK_ID = os.environ.get("NETWORK_ID", "base-sepolia")
USDC_ADDRESS = os.environ["USDC_ADDRESS"]
PAYMENT_RECIPIENT = os.environ["PAYMENT_RECIPIENT_ADDRESS"]
INR_PER_USDC = float(os.environ.get("INR_PER_USDC", "84"))

def _build_requirements(merchant, merchant_id, product_id, product, request_url):
    """x402 v1 paymentRequirements object."""
    price_usdc = product["price_inr"] / INR_PER_USDC
    max_amount_atomic = str(int(round(price_usdc * 1_000_000)))  # USDC has 6 decimals
    return {
        "scheme": "exact",
        "network": NETWORK_ID,
        "maxAmountRequired": max_amount_atomic,
        "resource": request_url,
        "description": f"{merchant['name']} — {product['name']}",
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
    # Path: /merchants/{merchantId}/products/{productId}/buy
    raw_path = event.get("rawPath") or event.get("path", "")
    parts = raw_path.strip("/").split("/")
    if len(parts) != 5 or parts[0] != "merchants" or parts[2] != "products" or parts[4] != "buy":
        return _resp(404, {"error": "not_found", "path": raw_path})

    merchant_id, product_id = parts[1], parts[3]
    merchant, product = find_product(merchant_id, product_id)
    if not merchant or not product:
        return _resp(404, {"error": "product_not_found"})

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    payment_header = headers.get("x-payment")

    # Build the canonical payment requirements (used in both 402 challenge and verify call)
    request_url = f"https://{event.get('requestContext', {}).get('domainName', 'localhost')}{raw_path}"
    requirements = _build_requirements(merchant, merchant_id, product_id, product, request_url)

    # Step A: no payment header → return 402 challenge
    if not payment_header:
        return _resp(402, {"x402Version": 1, "accepts": [requirements], "error": "X-PAYMENT header required"})

    # Step B: payment header present → decode, verify, settle
    try:
        payment_payload = json.loads(base64.b64decode(payment_header))
    except Exception as e:
        return _resp(400, {"error": "invalid_x_payment_header", "detail": str(e)})

    verify_resp = facilitator_client.verify(payment_payload, requirements)
    if not verify_resp.get("isValid"):
        return _resp(402, {"error": "verification_failed", "detail": verify_resp})

    settle_resp = facilitator_client.settle(payment_payload, requirements)
    if not settle_resp.get("success"):
        return _resp(402, {"error": "settlement_failed", "detail": settle_resp})

    tx_hash = settle_resp.get("transaction") or settle_resp.get("txHash")
    payer = (
        settle_resp.get("payer")
        or payment_payload.get("payload", {}).get("authorization", {}).get("from")
    )

    # Step C: fire Seedhape webhook (the unique value-add)
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

    # Step D: return 200 + content (per x402 spec, settled payment is in X-PAYMENT-RESPONSE header)
    settle_resp_b64 = base64.b64encode(json.dumps(settle_resp).encode()).decode()
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
```

### 4.6 File: `seller-lambda/template.yaml`
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Seedhape x402 seller endpoint

Globals:
  Function:
    Timeout: 30
    MemorySize: 512
    Runtime: python3.12

Parameters:
  PaymentRecipient:
    Type: String
  FacilitatorUrl:
    Type: String
    Default: https://api.cdp.coinbase.com/platform/v2/x402  # CONFIRM
  UsdcAddress:
    Type: String
    Default: "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
  CdpApiKeyId:
    Type: String
    NoEcho: true
  CdpApiKeySecret:
    Type: String
    NoEcho: true
  SeedhapeWebhookUrl:
    Type: String
  SeedhapeWebhookSecret:
    Type: String
    NoEcho: true

Resources:
  SellerFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./
      Handler: handler.lambda_handler
      Environment:
        Variables:
          NETWORK_ID: base-sepolia
          USDC_ADDRESS: !Ref UsdcAddress
          PAYMENT_RECIPIENT_ADDRESS: !Ref PaymentRecipient
          INR_PER_USDC: "84"
          FACILITATOR_URL: !Ref FacilitatorUrl
          CDP_API_KEY_ID: !Ref CdpApiKeyId
          CDP_API_KEY_SECRET: !Ref CdpApiKeySecret
          SEEDHAPE_WEBHOOK_URL: !Ref SeedhapeWebhookUrl
          SEEDHAPE_WEBHOOK_SECRET: !Ref SeedhapeWebhookSecret
      Events:
        Buy:
          Type: HttpApi
          Properties:
            Path: /merchants/{merchantId}/products/{productId}/buy
            Method: GET

Outputs:
  SellerApiUrl:
    Value: !Sub https://${ServerlessHttpApi}.execute-api.${AWS::Region}.amazonaws.com
```

### 4.7 Deploy + smoke test

```bash
cd seller-lambda
sam build
sam deploy --guided  # first time; saves config in samconfig.toml
# subsequent deploys: sam deploy

# Get API URL from stack outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name seedhape-x402-seller \
  --query 'Stacks[0].Outputs[?OutputKey==`SellerApiUrl`].OutputValue' \
  --output text)

# Smoke test 1: 402 challenge
curl -i "$API_URL/merchants/jaipur-textiles/products/kurta-indigo-m/buy"
# Expect: HTTP/1.1 402, body has x402Version + accepts[]
```

### 4.8 Definition of done
- [ ] `curl` to `/merchants/jaipur-textiles/products/kurta-indigo-m/buy` returns HTTP 402 with valid `accepts[]`
- [ ] CloudWatch logs show no errors on 402 path
- [ ] Webhook emitter, facilitator client, catalog modules all importable and unit-callable

---

## 5. Phase 2 — Payer agent (50 min)

### 5.1 Goal
A local Python script that uses an LLM (Claude) to autonomously decide what to buy from the Seedhape catalog, then executes the x402 flow against the Phase 1 Lambda. Settles real USDC on Base Sepolia.

### 5.2 Strategy
Use Anthropic's Python SDK directly with tool use — it's lighter than the full Strands SDK and you can frame as "Strands-compatible" in the README. The agent has three tools:
- `discover_merchants(category, region)`
- `browse_storefront(merchant_id)`
- `place_order(merchant_id, product_id)`

The `place_order` tool is where the x402 magic happens.

### 5.3 File: `agent/x402_client.py`

The 402 → sign → retry loop. **Look at `ref-x402` and `ref-aws/payer-agent` for the exact EIP-3009 typed-data payload structure.** Don't reinvent — port what works.

Approximate skeleton (Claude Code: refine against current x402 spec):

```python
"""x402 client: handles the 402 → EIP-3009 sign → retry handshake."""
import base64
import json
import os
import time
import urllib.request
import urllib.error
from typing import Optional

# Use CDP SDK for wallet operations — handles EIP-3009 signing under the hood.
# pip install cdp-sdk
from cdp import CdpClient  # adjust import per current cdp-sdk version

CDP_API_KEY_ID = os.environ["CDP_API_KEY_ID"]
CDP_API_KEY_SECRET = os.environ["CDP_API_KEY_SECRET"]
CDP_WALLET_SECRET = os.environ["CDP_WALLET_SECRET"]
WALLET_ADDRESS = os.environ["AGENT_WALLET_ADDRESS"]

_cdp_client: Optional[CdpClient] = None
def _get_cdp():
    global _cdp_client
    if _cdp_client is None:
        _cdp_client = CdpClient(
            api_key_id=CDP_API_KEY_ID,
            api_key_secret=CDP_API_KEY_SECRET,
            wallet_secret=CDP_WALLET_SECRET,
        )
    return _cdp_client


def _http_get(url: str, headers: dict | None = None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def _build_eip3009_authorization(requirements: dict, valid_seconds: int = 60) -> dict:
    """Construct the EIP-3009 transferWithAuthorization typed-data payload."""
    now = int(time.time())
    return {
        "from": WALLET_ADDRESS,
        "to": requirements["payTo"],
        "value": requirements["maxAmountRequired"],
        "validAfter": str(now - 10),
        "validBefore": str(now + valid_seconds),
        "nonce": "0x" + os.urandom(32).hex(),
    }


def _sign_authorization(authorization: dict, requirements: dict) -> str:
    """Sign EIP-712 typed data via CDP wallet. Returns 0x-prefixed signature."""
    cdp = _get_cdp()
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
            "name": requirements["extra"]["name"],
            "version": requirements["extra"]["version"],
            "chainId": 84532,  # Base Sepolia
            "verifyingContract": requirements["asset"],
        },
        "primaryType": "TransferWithAuthorization",
        "message": authorization,
    }
    # CDP SDK call — confirm exact method name in current SDK docs
    sig = cdp.evm.sign_typed_data(address=WALLET_ADDRESS, typed_data=typed_data)
    return sig


def _build_x_payment_header(requirements: dict) -> str:
    auth = _build_eip3009_authorization(requirements)
    signature = _sign_authorization(auth, requirements)
    payload = {
        "x402Version": 1,
        "scheme": "exact",
        "network": requirements["network"],
        "payload": {
            "signature": signature,
            "authorization": auth,
        },
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def fetch_with_payment(url: str) -> dict:
    """Hit the URL. If 402, sign and retry. Return the final 200 body as dict."""
    status, _, body = _http_get(url)
    if status == 200:
        return json.loads(body)
    if status != 402:
        raise RuntimeError(f"Unexpected status {status}: {body[:200]}")

    challenge = json.loads(body)
    requirements = challenge["accepts"][0]
    x_payment = _build_x_payment_header(requirements)
    status2, _, body2 = _http_get(url, headers={"X-PAYMENT": x_payment})
    if status2 != 200:
        raise RuntimeError(f"Payment retry failed {status2}: {body2[:500]}")
    return json.loads(body2)
```

> **Claude Code: this is the part most likely to have shape mismatches.** The exact x402 payload structure has evolved across versions. Before writing, read `ref-x402/python` (or wherever the Python implementation lives in the cloned coinbase/x402 repo) and align field names to the current spec. If a Python `x402` package exists on PyPI, use it — `pip install x402` — and skip building this module.

### 5.4 File: `agent/tools.py`

```python
"""Tool functions exposed to the agent's LLM."""
import os
from x402_client import fetch_with_payment

SELLER_API_BASE = os.environ["SELLER_API_BASE"]  # e.g. https://abc.execute-api.us-east-1.amazonaws.com

# Static merchant directory for MVP. In production this is a Seedhape /discover endpoint.
MERCHANT_DIRECTORY = [
    {
        "id": "jaipur-textiles",
        "name": "Jaipur Block Print Co",
        "category": "textiles",
        "region": "India / Rajasthan",
        "specialties": ["block-printed cotton", "kurtas", "scarves"],
    },
    {
        "id": "kerala-spices",
        "name": "Wayanad Spice Collective",
        "category": "spices",
        "region": "India / Kerala",
        "specialties": ["cardamom", "black pepper", "single-estate"],
    },
]

PRODUCT_CATALOG = {  # mirrors seller-lambda/catalog.py
    "jaipur-textiles": [
        {"id": "kurta-indigo-m", "name": "Hand-block-printed cotton kurta — indigo, M", "price_inr": 420},
        {"id": "kurta-indigo-l", "name": "Hand-block-printed cotton kurta — indigo, L", "price_inr": 420},
        {"id": "scarf-madder",   "name": "Madder-dyed cotton scarf", "price_inr": 280},
    ],
    "kerala-spices": [
        {"id": "cardamom-100g", "name": "Single-estate green cardamom, 100g", "price_inr": 350},
        {"id": "pepper-100g",   "name": "Tellicherry black pepper, 100g",     "price_inr": 180},
    ],
}

def discover_merchants(category: str | None = None, region: str | None = None) -> list:
    out = MERCHANT_DIRECTORY
    if category:
        out = [m for m in out if category.lower() in m["category"].lower()]
    if region:
        out = [m for m in out if region.lower() in m["region"].lower()]
    return out

def browse_storefront(merchant_id: str) -> list:
    return PRODUCT_CATALOG.get(merchant_id, [])

def place_order(merchant_id: str, product_id: str) -> dict:
    url = f"{SELLER_API_BASE}/merchants/{merchant_id}/products/{product_id}/buy"
    return fetch_with_payment(url)
```

### 5.5 File: `agent/buy.py`

The agent loop. Use Anthropic SDK with tool use.

```python
"""Procurement agent — autonomously fulfills wholesale buying instructions via x402."""
import json
import os
import sys
from anthropic import Anthropic
import tools

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

TOOLS = [
    {
        "name": "discover_merchants",
        "description": "Find Seedhape/Rasphia merchants matching a category and/or region. Returns a list of merchants with their IDs and specialties.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "e.g. 'textiles', 'spices'"},
                "region":   {"type": "string", "description": "e.g. 'India', 'Rajasthan'"},
            },
        },
    },
    {
        "name": "browse_storefront",
        "description": "List products at a specific merchant. Prices are in INR.",
        "input_schema": {
            "type": "object",
            "properties": {"merchant_id": {"type": "string"}},
            "required": ["merchant_id"],
        },
    },
    {
        "name": "place_order",
        "description": "Place an order for a product. This will autonomously pay in USDC on Base via the x402 protocol. Only call when you have decided on a specific product.",
        "input_schema": {
            "type": "object",
            "properties": {
                "merchant_id": {"type": "string"},
                "product_id":  {"type": "string"},
            },
            "required": ["merchant_id", "product_id"],
        },
    },
]

SYSTEM = (
    "You are a procurement agent for a Brooklyn boutique. You discover merchants, browse "
    "their catalogs, pick the best match for the user's request, and place orders. You pay "
    "autonomously using USDC on Base via the x402 protocol — the user does not need to "
    "approve each payment. Always explain your reasoning before placing an order. "
    "When you're done, summarize what you bought and from whom."
)

def run_tool(name: str, args: dict):
    fn = getattr(tools, name)
    return fn(**args)

def main():
    user_request = " ".join(sys.argv[1:]) or (
        "I need 1 hand-block-printed cotton kurta in indigo, size M, "
        "from a merchant in Rajasthan. Place the order."
    )
    print(f"\n🤖 USER REQUEST: {user_request}\n")
    messages = [{"role": "user", "content": user_request}]

    while True:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        # Print any text blocks (the agent's reasoning)
        for block in resp.content:
            if block.type == "text":
                print(f"💭 {block.text}")
        if resp.stop_reason == "end_turn":
            break
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    print(f"\n🔧 TOOL CALL: {block.name}({json.dumps(block.input)})")
                    try:
                        result = run_tool(block.name, block.input)
                        print(f"   ↳ {json.dumps(result, indent=2)[:400]}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                    except Exception as e:
                        print(f"   ↳ ERROR: {e}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {e}",
                            "is_error": True,
                        })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

if __name__ == "__main__":
    main()
```

### 5.6 File: `agent/.env.example`
```
ANTHROPIC_API_KEY=
CDP_API_KEY_ID=
CDP_API_KEY_SECRET=
CDP_WALLET_SECRET=
AGENT_WALLET_ADDRESS=
SELLER_API_BASE=
```

### 5.7 Run + smoke test
```bash
cd agent
python -m venv .venv && source .venv/bin/activate
pip install anthropic cdp-sdk  # or whatever the current CDP Python package is named
cp .env.example .env  # then fill it in
export $(cat .env | xargs)
python buy.py "Buy a kurta in indigo size M from a Jaipur merchant"
```

### 5.8 Definition of done
- [ ] Agent runs end-to-end and prints reasoning + tool calls
- [ ] `place_order` triggers a real EIP-3009 signature and Base Sepolia tx
- [ ] Tx is visible on https://sepolia.basescan.org/tx/{tx_hash}
- [ ] Agent prints the order confirmation including explorer URL
- [ ] Seller Lambda's CloudWatch logs show successful `verify` + `settle`

---

## 6. Phase 3 — Mock Seedhape webhook receiver (20 min)

### 6.1 Goal
Prove the bridge works. A second tiny Lambda that receives the `order.verified` webhook from Phase 1, verifies the HMAC, logs everything, and pretends to send a WhatsApp notification.

### 6.2 File: `webhook-receiver/handler.py`
```python
import hmac
import hashlib
import json
import os

WEBHOOK_SECRET = os.environ["SEEDHAPE_WEBHOOK_SECRET"]

def _verify(raw_body: bytes, signature: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[7:])

def lambda_handler(event, context):
    raw = (event.get("body") or "").encode("utf-8")
    if event.get("isBase64Encoded"):
        import base64
        raw = base64.b64decode(event["body"])
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    sig = headers.get("x-seedhape-signature", "")
    if not _verify(raw, sig):
        print(f"❌ Invalid signature. Got: {sig}")
        return {"statusCode": 401, "body": "invalid signature"}
    payload = json.loads(raw)
    print("✅ Verified order.verified webhook")
    print(json.dumps(payload, indent=2))

    # Pretend WhatsApp send
    inr = payload["amount_inr"]
    merchant = payload["merchant_name"]
    product = payload["product_name"]
    tx = payload["tx_hash"]
    msg = (
        f"🟢 [WhatsApp → {merchant}]\n"
        f"New order received: {product}\n"
        f"Amount: ₹{inr} (settled via x402 on Base)\n"
        f"Tx: https://sepolia.basescan.org/tx/{tx}\n"
        f"Order ID: {payload['order_id']}"
    )
    print(msg)
    return {"statusCode": 200, "body": json.dumps({"received": True, "whatsapp_simulated": msg})}
```

### 6.3 SAM template
Same shape as Phase 1, single function exposed via HttpApi at `POST /webhook`. Or fold this function into the Phase 1 stack as a second `AWS::Serverless::Function` resource — saves a deploy.

### 6.4 Wire it up
After deploying the receiver, get its URL and update Phase 1's `SEEDHAPE_WEBHOOK_URL` parameter. Redeploy seller stack.

### 6.5 Definition of done
- [ ] After running the agent, receiver's CloudWatch logs show the verified payload + the simulated WhatsApp message
- [ ] HMAC verification rejects a tampered request (test by sending a bad signature manually)

---

## 7. Phase 4 — Demo UI (40 min, optional but high-leverage)

### 7.1 Goal
A single static HTML page (one file, no build step) that streams the agent's reasoning + the on-chain tx + the merchant WhatsApp notification side-by-side. This is what wins the demo video.

### 7.2 Approach
Don't try to run the agent in the browser. Instead:
- Add a tiny Flask/FastAPI server (50 lines) that wraps `agent/buy.py` and streams its stdout via Server-Sent Events.
- The HTML connects via SSE and renders three columns: agent thinking, tx confirmations, mock WhatsApp.

If even this feels too long: **just record the terminal session** (`asciinema` or QuickTime) running the agent and the receiver's CloudWatch logs side by side. That's a perfectly good demo for 90 seconds. Skip the HTML.

### 7.3 File: `demo-ui/index.html` skeleton
```html
<!doctype html>
<html><head><meta charset="utf-8"><title>Seedhape × x402</title>
<style>
  body { font: 14px/1.5 ui-monospace, monospace; background: #0f1115; color: #e8e8e8; margin: 0; padding: 24px; }
  h1 { font-weight: 500; letter-spacing: 0.02em; }
  .grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; height: calc(100vh - 140px); }
  .pane { background: #1a1d24; border-radius: 12px; padding: 16px; overflow-y: auto; }
  .pane h2 { font-size: 13px; font-weight: 500; color: #aaa; margin: 0 0 12px; text-transform: uppercase; letter-spacing: 0.1em; }
  .agent .log { color: #c9b6ff; }
  .tool { color: #ffd089; }
  .tx   { color: #6dffb6; }
  .wa   { color: #80e0ff; }
  button { background: #5b8def; color: white; border: 0; padding: 10px 18px; border-radius: 8px; font-size: 14px; cursor: pointer; }
</style></head>
<body>
  <h1>Seedhape × x402 — Agentic commerce, real merchants</h1>
  <p style="color:#888">An autonomous agent in Brooklyn places a wholesale order with a merchant in Jaipur. Settled in USDC on Base in ~5 seconds. The merchant gets a WhatsApp notification in ₹INR.</p>
  <button onclick="run()">Run demo</button>
  <input id="prompt" style="width:60%;padding:8px;background:#1a1d24;color:white;border:1px solid #333;border-radius:6px;margin-left:12px" value="Buy 1 indigo kurta size M from a Rajasthan merchant" />
  <div class="grid" style="margin-top:16px">
    <div class="pane agent"><h2>Agent reasoning</h2><div id="agent"></div></div>
    <div class="pane"><h2>x402 + Base Sepolia</h2><div id="tx"></div></div>
    <div class="pane"><h2>Merchant WhatsApp</h2><div id="wa"></div></div>
  </div>
<script>
function run() {
  const prompt = document.getElementById('prompt').value;
  document.getElementById('agent').innerHTML = '';
  document.getElementById('tx').innerHTML = '';
  document.getElementById('wa').innerHTML = '';
  const es = new EventSource('/stream?prompt=' + encodeURIComponent(prompt));
  es.addEventListener('agent', e => append('agent', e.data));
  es.addEventListener('tool',  e => append('agent', e.data, 'tool'));
  es.addEventListener('tx',    e => append('tx', e.data, 'tx'));
  es.addEventListener('wa',    e => append('wa', e.data, 'wa'));
  es.addEventListener('done',  () => es.close());
}
function append(pane, text, cls='log') {
  const el = document.getElementById(pane);
  const d = document.createElement('div'); d.className = cls; d.textContent = text;
  el.appendChild(d); el.scrollTop = el.scrollHeight;
}
</script>
</body></html>
```

### 7.4 Definition of done
- [ ] You can hit the demo URL, click Run, and watch all three panes populate live
- [ ] Tx pane has a clickable link to basescan
- [ ] WhatsApp pane shows the simulated merchant notification

---

## 8. Phase 5 — README + pitch (30 min) ⭐ judging-critical

### 8.1 Goal
The README is what judges actually read. Make it sing.

### 8.2 README structure (use this outline)

```
# Seedhape × x402 — Agentic commerce for the real world

> An autonomous agent in NYC orders hand-block-printed kurtas from a merchant in Jaipur.
> Settled in USDC on Base in 5 seconds. The merchant gets a WhatsApp notification in ₹INR.
> They don't know crypto exists.

## Why this matters
Every other x402 demo monetizes APIs. We monetize the actual world. Seedhape is a payment
gateway for ~60M+ small Indian merchants on UPI. By bolting x402 onto Seedhape, we make
every Rasphia merchant reachable by every agent on the x402 Bazaar — without merchants
needing a wallet, KYC, or any crypto knowledge.

## Architecture
[ASCII diagram from §1]

## How it satisfies the judging criteria
- **Effective use of x402 + AWS**: Full x402 v1 flow (402 challenge → EIP-3009 sign → CDP
  facilitator verify+settle on Base Sepolia) implemented on AWS Lambda + API Gateway.
  Architecture is CloudFront + Lambda@Edge ready (one CDK migration; payment logic identical).
- **Innovation + real-world relevance**: First payment gateway bridging UPI rails
  (1.4B people) to x402 stablecoin rails. Merchants get paid in INR via WhatsApp; agents pay
  in USDC. The bridge is invisible to both ends.
- **Reusability + developer enablement**: 200-line Lambda handler is the entire seller-side
  integration. Any UPI gateway can fork this. Any Rasphia/Seedhape merchant gets agent
  payments for free — no merchant action required.
- **Effective use of Kiro**: [whatever you actually did with Kiro — e.g. "specs and final
  README authored in Kiro vibe-coding mode; steering rules guide our Python conventions"]

## Quickstart (5 minutes)
[Numbered steps to deploy + run]

## What ships next (post-hackathon)
- Move from API Gateway to CloudFront + Lambda@Edge for global edge latency
- Deploy agent to AgentCore Runtime for production scale
- USDC → INR off-ramp via partner — settle directly to merchant's UPI
- List `/agent-checkout` endpoints on x402 Bazaar for agent discovery
- Production HMAC rotation + idempotency keys on the webhook bridge

## Built with
- Coinbase Developer Platform (x402 facilitator, AgentKit wallet SDK)
- AWS Lambda, API Gateway, SAM
- Anthropic Claude (Sonnet 4.5) as the agent's reasoning model
- Base Sepolia (USDC settlement)
- [Kiro / Claude Code / both]
```

### 8.3 90-second pitch script

> **0:00–0:10** [Hook] "Right now, AI agents can pay $0.01 to read an article. They cannot buy a $5 kurta from a real human merchant. We changed that."
>
> **0:10–0:25** [Setup] "This is Seedhape — a payment gateway already powering thousands of small merchants in India on UPI rails. The merchants run their stores on WhatsApp. They've never heard of crypto."
>
> **0:25–0:45** [Demo] "Watch. I tell our procurement agent: *buy a hand-block-printed kurta from a Rajasthan merchant.* The agent discovers Jaipur Block Print Co, browses their catalog, picks one, and pays — autonomously."
> [SHOW: agent reasoning streams; tx hash appears on Base Sepolia explorer; WhatsApp notification appears with ₹420]
>
> **0:45–1:05** [The unlock] "Behind the scenes: the agent signed an EIP-3009 USDC transfer authorization. CDP's facilitator verified and settled on Base in under five seconds. Our Lambda fires Seedhape's existing `order.verified` webhook — same shape it always had — and Rasphia's WhatsApp pipeline runs unchanged. The merchant sees ₹420 received. They never see crypto."
>
> **1:05–1:30** [Why it wins] "Every other x402 demo is API monetization. We just connected the agentic economy to 60 million small merchants in emerging markets. Every Rasphia storefront is now reachable by every agent on the Bazaar — with zero merchant onboarding, zero wallet setup, zero crypto exposure. That's the unlock."

### 8.4 Definition of done
- [ ] README renders correctly on GitHub
- [ ] 90-second video recorded showing agent → tx → WhatsApp side-by-side
- [ ] Repo is public, judges can clone and run in <10 minutes from the README
- [ ] Architecture diagram (PNG/SVG) embedded in README

---

## 9. If you only have 2 hours (emergency MVP)

Cut these without mercy:
- ❌ Demo UI (Phase 4) — record terminal instead
- ❌ Pretty README polish — bullets are fine
- ❌ Multi-merchant catalog — one merchant, one product
- ❌ Agent LLM reasoning loop — replace with a hardcoded `place_order("jaipur-textiles", "kurta-indigo-m")` script. Frame as "the simplest possible demonstration of the protocol; LLM agent code is in `agent/buy.py` for production use."

What's still mandatory at 2 hours:
- ✅ Real on-chain Base Sepolia settlement (it must show on basescan)
- ✅ Seedhape webhook fires + receiver verifies HMAC
- ✅ README with the pitch
- ✅ The unique angle pitched clearly

---

## 10. Common gotchas — read this before you debug

1. **CDP facilitator URL/auth changes.** If `verify` returns 401 or 404, fetch current CDP docs and adjust. The `x402.org` facilitator is testnet-only and unauth'd — usable as a fallback if CDP auth becomes a time sink.
2. **EIP-3009 signature failures usually mean wrong domain fields.** `chainId` must be `84532` for Base Sepolia. `verifyingContract` must be the USDC contract, not the recipient. `name`/`version` must match what the USDC contract returns from its `name()` and `version()` calls — for Base Sepolia USDC it's `"USDC"` / `"2"`.
3. **`maxAmountRequired` must be a string** in atomic units (6 decimals for USDC). `420 / 84 = 5.0 USDC = "5000000"`. Don't pass floats.
4. **Lambda cold start can timeout the facilitator call** if you set Lambda timeout too low. Use 30s. Set `urllib` timeout to 25s.
5. **API Gateway lowercases all headers.** Always lowercase keys when reading `event["headers"]`. The `X-PAYMENT` header arrives as `x-payment`.
6. **`event["body"]` may be base64-encoded** when you POST binary-ish content. Check `isBase64Encoded` before parsing.
7. **CDP wallet needs both Base Sepolia ETH (gas) and USDC.** Run out of either and `settle` fails with cryptic errors.
8. **Don't redeploy the seller stack 50 times.** Use `sam local invoke` for handler iteration; only `sam deploy` when you're ready to test end-to-end.
9. **`anthropic` SDK model id**: use `"claude-sonnet-4-5"` or whatever the current Sonnet identifier is — verify against https://docs.claude.com/en/docs/about-claude/models.

---

## 11. Final checklist (do this before submitting)

- [ ] Repo is public on GitHub
- [ ] README has pitch, architecture diagram, judging-criteria mapping, quickstart
- [ ] At least one Base Sepolia tx hash linked from README — judges should click and see real settlement
- [ ] Seedhape webhook receiver logs are screenshotted in README showing the bridge working
- [ ] 90-second demo video uploaded (Loom / YouTube unlisted)
- [ ] If you used Kiro at all: Kiro spec/steering files committed, mentioned in README
- [ ] `.env.example` files in all three projects, no real secrets committed
- [ ] One sentence in README explicitly saying "uses CDP's x402 Facilitator on Base" (judges grep for this)
- [ ] One sentence saying "deployed on AWS Lambda + API Gateway, CloudFront + Lambda@Edge production-ready"

Ship it.
