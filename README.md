# Seedhape x402 - Agentic commerce for the real world

An autonomous agent in NYC orders from a merchant in Jaipur, settles in USDC on Base Sepolia, and the merchant receives a Seedhape-style `order.verified` webhook in INR terms.

## Why this matters
Most x402 demos monetize APIs. This demo bridges x402 payments into physical commerce workflows used by small merchants.

## Architecture
See [docs/architecture.md](./docs/architecture.md).

## Judging criteria mapping
- Effective use of x402 + AWS: seller flow is deployed on AWS Lambda + API Gateway, using CDP's x402 Facilitator on Base.
- Innovation + real-world relevance: links agentic USDC payments to merchant-facing INR order events.
- Reusability: drop-in seller Lambda and webhook bridge with minimal integration surface.
- Production direction: CloudFront + Lambda@Edge ready; payment logic remains the same.

## Quickstart
1. Deploy webhook receiver.
```bash
cd webhook-receiver
sam build
sam deploy --guided --stack-name seedhape-x402-webhook
```
2. Capture webhook URL from stack output and deploy seller lambda.
```bash
cd ../seller-lambda
sam build
sam deploy --guided --stack-name seedhape-x402-seller
```
3. Smoke test 402 challenge.
```bash
curl -i "$SELLER_API_BASE/merchants/jaipur-textiles/products/kurta-indigo-m/buy"
```
4. Run local agent.
```bash
cd ../agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a; source .env; set +a
python buy.py "Buy an indigo kurta size M from a Jaipur merchant"
```

## Mandatory demo proof points
- Real Base Sepolia settlement tx hash appears in agent output and seller response.
- Webhook receiver logs verified signature + simulated WhatsApp message.

## Constants
- Network: `base-sepolia`
- USDC: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- Demo FX: `1 USDC = 84 INR`

## Notes
- CDP facilitator base URL: `https://api.cdp.coinbase.com/platform/v2/x402`
- CDP auth uses `CDP_API_KEY_ID` + `CDP_API_KEY_SECRET`.
- Fallback facilitator for testnet experiments: `https://x402.org/facilitator`
