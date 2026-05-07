# Architecture

```
[Local Python agent: Anthropic Claude + tool loop]
                         |
                         | GET /merchants/{id}/products/{id}/buy
                         v
      +-----------------------------------------------+
      | AWS API Gateway + Lambda (seller-lambda)      |
      | - 402 challenge                               |
      | - verify + settle via CDP x402 facilitator    |
      | - emit Seedhape-style order.verified webhook  |
      +---------------------+-------------------------+
                            |
                            v
                 Base Sepolia USDC settlement

      +-----------------------------------------------+
      | AWS API Gateway + Lambda (webhook-receiver)   |
      | - HMAC verify                                 |
      | - logs order.verified                         |
      | - simulates merchant WhatsApp notification    |
      +-----------------------------------------------+
```

Judging fit:
- Effective x402 + AWS use: seller endpoint on Lambda/API Gateway with real facilitator verify/settle.
- Innovation: bridges agent payments to merchant-facing INR webhook flow.
- Reusability: modular handler + webhook adapter, easy for other UPI gateways to fork.
