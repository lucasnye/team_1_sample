import sys
import os
import time



sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from acp_sdk.client import VirtualsACP
from acp_sdk.configs import BASE_SEPOLIA_CONFIG
from acp_sdk.env import EnvSettings
from acp_sdk.models import ACPJobPhase


from dotenv import load_dotenv

load_dotenv(override=True)

def evaluator():
    env = EnvSettings()
    

    # Initialize the ACP client
    acp_client = VirtualsACP(
        wallet_private_key=env.WHITELISTED_WALLET_PRIVATE_KEY,
        agent_wallet_address=env.BUYER_WALLET_ADDRESS,
        config=BASE_SEPOLIA_CONFIG,
    )
    
    active_jobs = acp_client.get_active_jobs()
    print(active_jobs[0].phase)
    print(ACPJobPhase(1))    
    print(ACPJobPhase.NEGOTIATION)
    
    print(ACPJobPhase.NEGOTIATION == ACPJobPhase(1))    
    print(active_jobs[0].phase == ACPJobPhase(1))    

if __name__ == "__main__":
    evaluator()
