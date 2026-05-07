"""In-memory catalog. Real Seedhape pulls from merchant DB."""

CATALOG = {
    "jaipur-textiles": {
        "name": "Jaipur Block Print Co",
        "location": "Jaipur, Rajasthan",
        "products": {
            "kurta-indigo-m": {
                "name": "Hand-block-printed cotton kurta - indigo, M",
                "price_inr": 4,
                "stock": 200,
            },
            "kurta-indigo-l": {
                "name": "Hand-block-printed cotton kurta - indigo, L",
                "price_inr": 4,
                "stock": 150,
            },
            "scarf-madder": {
                "name": "Madder-dyed cotton scarf",
                "price_inr": 2,
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
                "price_inr": 3,
                "stock": 500,
            },
            "pepper-100g": {
                "name": "Tellicherry black pepper, 100g",
                "price_inr": 1,
                "stock": 1000,
            },
        },
    },
}


def find_product(merchant_id: str, product_id: str):
    merchant = CATALOG.get(merchant_id)
    if not merchant:
        return None, None
    product = merchant["products"].get(product_id)
    if not product:
        return merchant, None
    return merchant, product


def list_merchants() -> list[dict]:
    merchants = []
    for merchant_id, merchant in CATALOG.items():
        name_l = merchant["name"].lower()
        category = "textiles"
        if "spice" in name_l or "pepper" in name_l or "cardamom" in name_l:
            category = "spices"
        merchants.append(
            {
                "id": merchant_id,
                "name": merchant["name"],
                "category": category,
                "region": f"India / {merchant['location'].split(',')[-1].strip()}",
                "location": merchant["location"],
                "specialties": [p["name"] for p in merchant["products"].values()][:3],
            }
        )
    return merchants


def list_products(merchant_id: str) -> list[dict] | None:
    merchant = CATALOG.get(merchant_id)
    if not merchant:
        return None
    return [
        {
            "id": product_id,
            "name": product["name"],
            "price_inr": product["price_inr"],
            "stock": product["stock"],
        }
        for product_id, product in merchant["products"].items()
    ]
