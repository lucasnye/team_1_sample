from collections.abc import Callable
from datetime import datetime, timedelta
import json
import sys
import os
import time


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from acp_python.client import VirtualsACP
from acp_python.models import ACPJobPhase, IACPJob
from acp_python.configs import BASE_SEPOLIA_CONFIG
from acp_python.utils.job_actions import pay_job



def test_buyer():
    def on_new_task(job: IACPJob):
        job_phase = ACPJobPhase(job.phase) if isinstance(job.phase, int) else job.phase
        if job_phase == ACPJobPhase.NEGOTIATION:
            # Check if there's a memo that indicates next phase is TRANSACTION
            for memo in job.memos:
                next_phase = ACPJobPhase(memo.next_phase) if isinstance(memo.next_phase, int) else memo.next_phase
                if next_phase == ACPJobPhase.TRANSACTION:
                    print("Paying job", job.id)
                    pay_job(acp, job.id, job.memos, 2)
                    break
        elif job_phase == ACPJobPhase.COMPLETED:
            print("Job completed", job)
            
    acp = VirtualsACP(
        wallet_private_key="xxx",
        agent_wallet_address="xxx",
        config=BASE_SEPOLIA_CONFIG,
        on_new_task=on_new_task
    )
    
    agents = acp.browse_agents(keyword="meme", cluster="999")
    
    job_offering = agents[2].offerings[0]
    
    job_id = job_offering.initiate_job(
        price=float(2),
        service_requirement="Help me generate a meme",
        expired_at=datetime.now() + timedelta(days=1)
    )
    
    print(f"Job {job_id} initiated")
    
    while True:
        print("Listening for next steps...")
        time.sleep(30)

if __name__ == "__main__":
    test_buyer()
