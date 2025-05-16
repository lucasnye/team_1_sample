from collections.abc import Callable
import sys
import os
import time
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from acp_python.client import VirtualsACP
from acp_python.models import ACPJobPhase, IACPJob
from acp_python.configs import BASE_SEPOLIA_CONFIG
from acp_python.utils.job_actions import respond_job, deliver_job

def seller():
    def on_new_task(job: IACPJob):
        # Convert job.phase to ACPJobPhase enum if it's an integer
        job_phase = ACPJobPhase(job.phase) if isinstance(job.phase, int) else job.phase
        if job_phase == ACPJobPhase.REQUEST:
            # Check if there's a memo that indicates next phase is NEGOTIATION
            for memo in job.memos:
                next_phase = ACPJobPhase(memo.next_phase) if isinstance(memo.next_phase, int) else memo.next_phase
                if next_phase == ACPJobPhase.NEGOTIATION:
                    respond_job(acp_client,job.id, job.memos, True)
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
                    deliver_job(
                        acp_client,
                        job.id,
                        job.memos,
                        json.dumps(delivery_data),
                    )
                    break

    # Initialize the ACP client
    acp_client = VirtualsACP(
        wallet_private_key="xxx",
        agent_wallet_address="xxx",
        config=BASE_SEPOLIA_CONFIG,
        on_new_task=on_new_task
    )
    
    # Keep the script running to listen for new tasks
    while True:
        print("Waiting for new task...")
        time.sleep(30)

if __name__ == "__main__":
    seller()
