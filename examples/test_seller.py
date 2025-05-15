from collections.abc import Callable
import sys
import os
import time
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from virtuals_acp.client import VirtualsACP
from virtuals_acp.models import ACPJobPhase, MemoType, IACPAgent
from virtuals_acp.configs import BASE_SEPOLIA_CONFIG

def seller():
    def on_new_task(job: IACPAgent, callback: Callable):
        if job.phase == ACPJobPhase.REQUEST:
            # Check if there's a memo that indicates next phase is NEGOTIATION
            for memo in job.memos:
                if memo.next_phase == ACPJobPhase.NEGOTIATION:
                    print("Responding to job", job)
                    # Respond to the memo with acceptance
                    acp_client.respond_to_job_memo(memo.id, True)
                    callback(True)
                    break
        elif job.phase == ACPJobPhase.TRANSACTION:
            # Check if there's a memo that indicates next phase is EVALUATION
            for memo in job.memos:
                if memo.next_phase == ACPJobPhase.EVALUATION:
                    print("Delivering job", job)
                    # Submit the deliverable
                    delivery_data = {
                        "type": "url",
                        "value": "https://example.com"
                    }
                    acp_client.submit_job_deliverable(
                        job.id,
                        json.dumps(delivery_data),
                        MemoType.OBJECT_URL
                    )
                    callback(True)
                    break

    # Initialize the ACP client
    acp_client = VirtualsACP(
        wallet_private_key="0xc693f94783e4ecfa7e68d0d2c29bb73e66fe3848e0b6011803d15bc07b82227b",
        agent_wallet_address="0x54850F1936854ed5682CbB8A61f05C448262B761",
        config=BASE_SEPOLIA_CONFIG,
        on_new_task=on_new_task
    )
    
    # Keep the script running to listen for new tasks
    while True:
        print("Waiting for new task...")
        time.sleep(30)

if __name__ == "__main__":
    seller()
