from collections.abc import Callable
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from virtuals_acp.client import VirtualsACP
from virtuals_acp.models import ACPJobPhase
from virtuals_acp.configs import BASE_SEPOLIA_CONFIG
from virtuals_acp import AcpJob

def evaluator():
    def on_evaluate(job: AcpJob, callback: Callable):
        print("Evaluation function called", job)
        # Find the deliverable memo
        for memo in job.memos:
            if memo.next_phase == ACPJobPhase.COMPLETED:
                # Evaluate the deliverable by accepting it
                acp_client.evaluate_job_delivery(memo.id, True)
                callback(True)
                break

    # Initialize the ACP client
    acp_client = VirtualsACP(
        wallet_private_key="60e3438e1cd3b3ca6afa310e3350a59fa8a51ba42266c1281dee237b8ec264f2",
        agent_wallet_address="0x9cb1497E8192FDCc60c4dC6D3B01F40D9215ad50",
        config=BASE_SEPOLIA_CONFIG,
        on_evaluate=on_evaluate
    )
    
    # Keep the script running to listen for evaluation tasks
    while True:
        print("Waiting for evaluation tasks...")
        time.sleep(30)

if __name__ == "__main__":
    evaluator()
