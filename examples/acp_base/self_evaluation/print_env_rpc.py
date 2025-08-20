# print_env_rpc.py
from dotenv import load_dotenv
import os
load_dotenv(override=True)
print("RPC_URL =", os.getenv("RPC_URL"))
print("CHAIN_ENV =", os.getenv("CHAIN_ENV"))
print("CHAIN_ID =", os.getenv("CHAIN_ID"))
print("BASE_SEPOLIA_RPC_URL =", os.getenv("BASE_SEPOLIA_RPC_URL"))