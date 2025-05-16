from collections.abc import Callable
import sys
import os
import time


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from acp_python.utils.job_actions import evaluate_job
from acp_python.client import VirtualsACP
from acp_python.models import ACPJobPhase, IACPJob
from acp_python.configs import BASE_SEPOLIA_CONFIG
from acp_python import AcpJob

def evaluator():
    def on_evaluate(job: IACPJob):
        print("Evaluation function called", job.memos)
        # Find the deliverable memo
        for memo in job.memos:
            next_phase = ACPJobPhase(memo.next_phase) if isinstance(memo.next_phase, int) else memo.next_phase
            if next_phase == ACPJobPhase.COMPLETED:
                # Evaluate the deliverable by accepting it
                evaluate_job(acp_client, job.memos, True)
                break

    # Initialize the ACP client
    acp_client = VirtualsACP(
        wallet_private_key="xxx",
        agent_wallet_address="xxx",
        config=BASE_SEPOLIA_CONFIG,
        on_evaluate=on_evaluate
    )
    
    # Keep the script running to listen for evaluation tasks
    while True:
        print("Waiting for evaluation tasks...")
        time.sleep(30)

if __name__ == "__main__":
    evaluator()
