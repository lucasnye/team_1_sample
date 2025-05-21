from datetime import datetime, timedelta
import sys
import os
import time


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from acp_sdk.client import VirtualsACP
from acp_sdk.job import AcpJob
from acp_sdk.models import ACPJobPhase
from acp_sdk.configs import BASE_SEPOLIA_CONFIG
from acp_sdk.env import EnvSettings

from dotenv import load_dotenv

load_dotenv(override=True)


def test_buyer():
    env = EnvSettings()

    def on_new_task(job: AcpJob):
        if job.phase == ACPJobPhase.NEGOTIATION:
            # Check if there's a memo that indicates next phase is TRANSACTION
            for memo in job.memos:
                if memo.next_phase == ACPJobPhase.TRANSACTION:
                    print("Paying job", job.id)
                    job.pay(2)
                    break
        elif job.phase == ACPJobPhase.COMPLETED:
            print("Job completed", job)
    
    def on_evaluate(job: AcpJob):
        print("Evaluation function called", job.memos)
        # Find the deliverable memo
        for memo in job.memos:
            if memo.next_phase == ACPJobPhase.COMPLETED:
                # Evaluate the deliverable by accepting it
                job.evaluate(True)
                break
            
    acp = VirtualsACP(
        wallet_private_key=env.WHITELISTED_WALLET_PRIVATE_KEY,
        agent_wallet_address=env.BUYER_WALLET_ADDRESS,
        config=BASE_SEPOLIA_CONFIG,
        on_new_task=on_new_task,
        on_evaluate=on_evaluate
    )
    
    agents = acp.browse_agents(keyword="meme", cluster="999")
    
    job_offering = agents[1].offerings[0]
    
    job_id = job_offering.initiate_job(
        price=float(2),
        service_requirement="Help me generate a meme",
        expired_at=datetime.now() + timedelta(days=1),
        # evaluator_address=env.BUYER_WALLET_ADDRESS
    )
    
    print(f"Job {job_id} initiated")
    
    while True:
        print("Listening for next steps...")
        time.sleep(30)

if __name__ == "__main__":
    test_buyer()
