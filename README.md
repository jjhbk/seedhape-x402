# Seedhape × x402 — Agentic Commerce for Real Merchants

> A local AI agent places a wholesale order from a Jaipur merchant, pays in USDC via x402 on Base Sepolia, and the merchant-side system receives a normal INR-oriented `order.verified` webhook.

## At a Glance
**Problem:** Most x402 demos monetize APIs, not physical commerce.

**What this demo proves:**
- Agents can buy real merchant goods, not just API responses.
- Payment is autonomous (`402 -> pay -> retry`) and settles on-chain.
- Merchant workflows stay unchanged (webhook + INR context), no crypto UX required.

## Single-Look Architecture
```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Buyer Side                                                                 │
│ Local Procurement Agent (Anthropic tools + x402 client)                    │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ GET /merchants/{m}/products/{p}/buy
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Seller Side (AWS API Gateway + Lambda)                                     │
│ 1) No payment header -> return HTTP 402 + x402 accepts[]                   │
│ 2) With X-PAYMENT -> facilitator verify + settle                           │
│ 3) On success -> emit Seedhape-style order.verified webhook                │
└───────────────┬──────────────────────────────────────────────┬──────────────┘
                │                                              │
                ▼                                              ▼
     Base Sepolia (USDC settlement)                 Webhook Receiver (Lambda)
     tx hash + explorer proof                       HMAC verify + WhatsApp sim log
```

## Protocol Sequence (Technical)
```text
Agent -> Seller: GET /buy
Seller -> Agent: 402 + paymentRequirements (x402Version=1, exact, USDC)
Agent: Build EIP-3009 authorization + sign EIP-712
Agent -> Seller: GET /buy + X-PAYMENT(base64 payload)
Seller -> Facilitator: POST /verify
Seller -> Facilitator: POST /settle
Facilitator -> Seller: success + tx hash
Seller -> Webhook Receiver: order.verified (HMAC signed)
Seller -> Agent: 200 confirmed + explorer_url
```

## Why This Makes Sense
- **Fits current merchant ops:** merchants already consume order webhooks and INR amounts.
- **Fits agentic economics:** agents can pay instantly with stablecoins over open rails.
- **Bridge model:** crypto-native payer side + fiat-native merchant side without replatforming.

## What’s in This Repo
```text
seedhape-x402-mvp/
├── seller-lambda/       # x402 paywalled merchant endpoint (core logic)
├── webhook-receiver/    # mock Seedhape receiver + HMAC verification
├── agent/               # autonomous buyer (discover, browse, place_order)
├── demo-ui/             # live SSE demo UI for judge walkthrough
└── docs/                # architecture notes
```

## Judge-Focused Acceptance Signals
- `GET /buy` returns HTTP `402` with valid x402 `accepts[]`.
- Agent retries with signed `X-PAYMENT` and receives `200 confirmed`.
- Settlement tx hash resolves on Base Sepolia explorer.
- Webhook receiver logs verified `order.verified` event and simulated WhatsApp message.

## Quick Demo Run
1. Deploy webhook receiver.
```bash
cd webhook-receiver
sam build
sam deploy --guided --stack-name seedhape-x402-webhook
```
2. Deploy seller lambda with webhook URL + CDP credentials.
```bash
cd ../seller-lambda
sam build --use-container
sam deploy --stack-name seedhape-x402-seller --region us-east-2 --capabilities CAPABILITY_IAM \
  --parameter-overrides \
  PaymentRecipient="$PAYMENT_RECIPIENT_ADDRESS" \
  FacilitatorUrl="$FACILITATOR_URL" \
  UsdcAddress="$USDC_ADDRESS" \
  CdpApiKeyId="$CDP_API_KEY_ID" \
  CdpApiKeySecret="$CDP_API_KEY_SECRET" \
  SeedhapeWebhookUrl="$SEEDHAPE_WEBHOOK_URL" \
  SeedhapeWebhookSecret="$SEEDHAPE_WEBHOOK_SECRET"
```
3. Run agent directly.
```bash
cd ../agent
source .venv/bin/activate
set -a; source .env; set +a
python buy.py "Buy an indigo kurta size M from a Jaipur merchant"
```
4. Optional live UI demo.
```bash
cd ../demo-ui
source ../agent/.venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8081 --reload
```
Open `http://localhost:8081`.

## Current Demo Configuration
- Network: `base-sepolia`
- USDC: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- FX peg for MVP: `1 USDC = 84 INR` (or env-configured)
- Facilitator URL default: `https://api.cdp.coinbase.com/platform/v2/x402`

## Production Next Steps
- Move seller edge to CloudFront + Lambda@Edge (same payment logic).
- Add idempotency keys + webhook replay protection storage.
- Add USDC->INR off-ramp integration for merchant settlement.
- Publish merchant `/buy` resources to x402 Bazaar discovery.
