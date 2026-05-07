"""Procurement agent: discovers merchants and places x402-paid orders."""

import json
import os
import sys

from anthropic import Anthropic

import tools

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

TOOLS = [
    {
        "name": "discover_merchants",
        "description": "Find merchants matching category/region.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "region": {"type": "string"},
            },
        },
    },
    {
        "name": "browse_storefront",
        "description": "List products for a merchant.",
        "input_schema": {
            "type": "object",
            "properties": {"merchant_id": {"type": "string"}},
            "required": ["merchant_id"],
        },
    },
    {
        "name": "place_order",
        "description": "Place an order and pay via x402.",
        "input_schema": {
            "type": "object",
            "properties": {
                "merchant_id": {"type": "string"},
                "product_id": {"type": "string"},
            },
            "required": ["merchant_id", "product_id"],
        },
    },
]

SYSTEM = (
    "You are a procurement agent for a Brooklyn boutique. Discover merchants, browse "
    "catalogs, choose the best match, then place the order. Explain your reasoning before "
    "calling place_order."
)


def run_tool(name: str, args: dict):
    fn = getattr(tools, name)
    return fn(**args)


def main():
    user_request = " ".join(sys.argv[1:]) or (
        "I need 1 hand-block-printed cotton kurta in indigo, size M, "
        "from a merchant in Rajasthan. Place the order."
    )
    print(f"USER REQUEST: {user_request}\n")
    messages = [{"role": "user", "content": user_request}]

    while True:
        resp = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
            max_tokens=2048,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        for block in resp.content:
            if block.type == "text":
                print(f"THINKING: {block.text}")

        if resp.stop_reason == "end_turn":
            break

        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                print(f"\nTOOL CALL: {block.name}({json.dumps(block.input)})")
                try:
                    result = run_tool(block.name, block.input)
                    print(f"RESULT: {json.dumps(result, indent=2)[:500]}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        }
                    )
                except Exception as exc:
                    print(f"ERROR: {exc}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {exc}",
                            "is_error": True,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        break


if __name__ == "__main__":
    main()
