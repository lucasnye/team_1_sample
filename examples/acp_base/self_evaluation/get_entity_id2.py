import os
from dotenv import load_dotenv
from web3 import Web3

# We’ll try to detect the registry address from the package; or you can set ACP_REGISTRY_ADDRESS in .env
def find_registry_address():
    env_addr = os.getenv("ACP_REGISTRY_ADDRESS")
    if env_addr and env_addr.startswith("0x") and len(env_addr) == 42:
        return env_addr

    try:
        import virtuals_acp.contract_manager as cm
        for name in dir(cm):
            if "REGISTRY" in name.upper() and "ADDRESS" in name.upper():
                value = getattr(cm, name)
                if isinstance(value, str) and value.startswith("0x") and len(value) == 42:
                    return value
    except Exception:
        pass

    raise RuntimeError(
        "Could not find ACP Registry address. "
        "Set ACP_REGISTRY_ADDRESS=0x... in .env or open virtuals_acp/contract_manager.py and copy the registry address."
    )

# Two common ABI shapes; we’ll try both
ABI_getEntityId = [{
  "inputs":[{"internalType":"address","name":"wallet","type":"address"}],
  "name":"getEntityId",
  "outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
  "stateMutability":"view","type":"function"
}]
ABI_entityIds = [{
  "inputs":[{"internalType":"address","name":"","type":"address"}],
  "name":"entityIds",
  "outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
  "stateMutability":"view","type":"function"
}]

def lookup_id(w3, registry_addr, wallet):
    wallet = Web3.to_checksum_address(wallet)
    # Try getEntityId
    try:
        c = w3.eth.contract(address=registry_addr, abi=ABI_getEntityId)
        return c.functions.getEntityId(wallet).call()
    except Exception:
        pass
    # Try mapping entityIds
    try:
        c = w3.eth.contract(address=registry_addr, abi=ABI_entityIds)
        return c.functions.entityIds(wallet).call()
    except Exception:
        pass
    raise RuntimeError("Registry ABI did not match expected functions.")

def main():
    load_dotenv()
    rpc = os.getenv("RPC_URL")
    buyer = os.getenv("BUYER_AGENT_WALLET_ADDRESS")
    seller = os.getenv("SELLER_AGENT_WALLET_ADDRESS")
    assert rpc, "RPC_URL is missing in .env"
    assert buyer and seller, "Buyer/Seller wallet addresses missing in .env"

    w3 = Web3(Web3.HTTPProvider(rpc))
    assert w3.is_connected(), f"Cannot connect to RPC: {rpc}"
    print("Connected. ChainId:", w3.eth.chain_id)

    registry_addr = Web3.to_checksum_address(find_registry_address())
    print("Using ACP Registry at:", registry_addr)

    buyer_id = lookup_id(w3, registry_addr, buyer)
    seller_id = lookup_id(w3, registry_addr, seller)

    print(f"\nBUYER  {buyer} -> entityId = {buyer_id}")
    print(f"SELLER {seller} -> entityId = {seller_id}")

if __name__ == "__main__":
    main()
