import sys
import os
import time


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from acp_sdk.utils.job_actions import evaluate_job
from acp_sdk.client import VirtualsACP
from acp_sdk.models import ACPJobPhase, IACPJob
from acp_sdk.configs import BASE_SEPOLIA_CONFIG
from acp_sdk.env import EnvSettings

from dotenv import load_dotenv

load_dotenv(override=True)

def evaluator():
    env = EnvSettings()

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
        wallet_private_key=env.WHITELISTED_WALLET_PRIVATE_KEY,
        agent_wallet_address=env.EVALUATOR_WALLET_ADDRESS,
        config=BASE_SEPOLIA_CONFIG,
        on_evaluate=on_evaluate
    )
    
    # Keep the script running to listen for evaluation tasks
    while True:
        print("Waiting for evaluation tasks...")
        time.sleep(30)

if __name__ == "__main__":
    evaluator()
