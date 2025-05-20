from collections.abc import Callable
import sys
import os
import time
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from acp_sdk.client import VirtualsACP
from acp_sdk.models import ACPJobPhase
from acp_sdk.configs import BASE_SEPOLIA_CONFIG
from acp_sdk.env import EnvSettings
from acp_sdk.job import AcpJob

from dotenv import load_dotenv

load_dotenv()

def seller():
    env = EnvSettings()

    def on_new_task(job: AcpJob):
        print(job,'job')
        # Handle phase conversion regardless of input type
        
        job_phase = ACPJobPhase(job.phase) if isinstance(job.phase, int) else job.phase
        if job.phase == ACPJobPhase.REQUEST:
            print(job,'job_phase')
            # Check if there's a memo that indicates next phase is NEGOTIATION
            for memo in job.memos:
                next_phase = ACPJobPhase(memo.next_phase) if isinstance(memo.next_phase, int) else memo.next_phase
                if next_phase == ACPJobPhase.NEGOTIATION:
                    print("negotiation")
                    job.respond(True)
                    break
        elif job_phase == ACPJobPhase.TRANSACTION:
            # Check if there's a memo that indicates next phase is EVALUATION
            for memo in job.memos:
                next_phase = ACPJobPhase(memo.next_phase) if isinstance(memo.next_phase, int) else memo.next_phase
                if next_phase == ACPJobPhase.EVALUATION:
                    print("Delivering job", job)
                    delivery_data = {
                        "type": "url",
                        "value": "https://example.com"
                    }
                    job.deliver(json.dumps(delivery_data))
                    break

    # Initialize the ACP client
    acp_client = VirtualsACP(
        wallet_private_key=env.WHITELISTED_WALLET_PRIVATE_KEY,
        agent_wallet_address=env.SELLER_WALLET_ADDRESS,
        config=BASE_SEPOLIA_CONFIG,
        on_new_task=on_new_task
    )
    
    # Keep the script running to listen for new tasks
    while True:
        print("Waiting for new task...")
        time.sleep(30)

if __name__ == "__main__":
    seller()
