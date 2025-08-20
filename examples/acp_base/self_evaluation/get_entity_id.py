import os
from dotenv import load_dotenv
from web3 import Web3
from virtuals_acp.contract_manager import ACPRegistry

load_dotenv()

rpc_url = os.getenv("RPC_URL")
buyer_addr = os.getenv("BUYER_AGENT_WALLET_ADDRESS")
seller_addr = os.getenv("SELLER_AGENT_WALLET_ADDRESS")

w3 = Web3(Web3.HTTPProvider(rpc_url))
assert w3.is_connected(), f"RPC not connected: {rpc_url}"

registry = ACPRegistry(w3)

buyer_id = registry.get_entity_id(buyer_addr)
seller_id = registry.get_entity_id(seller_addr)

print(f"BUYER:  {buyer_addr} -> entityId={buyer_id}")
print(f"SELLER: {seller_addr} -> entityId={seller_id}")
