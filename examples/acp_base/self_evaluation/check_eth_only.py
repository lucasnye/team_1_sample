# check_eth_only.py
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_utils import from_wei

load_dotenv()
RPC = os.getenv("RPC_URL")
BUYER = os.getenv("BUYER_AGENT_WALLET_ADDRESS")

w3 = Web3(Web3.HTTPProvider(RPC))
assert w3.is_connected(), f"RPC not connected: {RPC}"
print("ChainId:", w3.eth.chain_id)  # should be 84532

def bal(addr):
    return from_wei(w3.eth.get_balance(Web3.to_checksum_address(addr)), "ether")

print("Buyer  ETH:", bal(BUYER))
pk = os.getenv("WHITELISTED_WALLET_PRIVATE_KEY")
if pk and pk.startswith("0x"):
    from eth_account import Account
    signer = Account.from_key(pk).address
    print("Signer ETH:", bal(signer))
else:
    print("Signer ETH: (no PK loaded)")
