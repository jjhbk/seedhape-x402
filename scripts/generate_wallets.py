"""Generate demo EVM wallets for payer and recipient."""

from eth_account import Account


def main():
    payer = Account.create()
    recipient = Account.create()

    print("=== PAYER WALLET (fund this) ===")
    print(f"ADDRESS={payer.address}")
    print(f"PRIVATE_KEY={payer.key.hex()}")
    print()
    print("=== RECIPIENT WALLET (treasury) ===")
    print(f"ADDRESS={recipient.address}")
    print(f"PRIVATE_KEY={recipient.key.hex()}")
    print()
    print("Store these securely. Do not commit private keys.")


if __name__ == "__main__":
    main()
