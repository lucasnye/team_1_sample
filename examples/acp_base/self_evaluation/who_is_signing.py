# who_is_signing.py
import os
from dotenv import load_dotenv
from eth_account import Account

load_dotenv()
pk = os.getenv("WHITELISTED_WALLET_PRIVATE_KEY")
assert pk and pk.startswith("0x"), "Missing WHITELISTED_WALLET_PRIVATE_KEY in .env"
signer = Account.from_key(pk).address
print("Signer (from private key):", signer)
print("BUYER_AGENT_WALLET_ADDRESS:", os.getenv("BUYER_AGENT_WALLET_ADDRESS"))
print("SELLER_AGENT_WALLET_ADDRESS:", os.getenv("SELLER_AGENT_WALLET_ADDRESS"))
