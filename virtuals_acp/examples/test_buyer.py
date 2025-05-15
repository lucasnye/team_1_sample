from collections.abc import Callable
from datetime import datetime, timedelta
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from virtuals_acp.client import VirtualsACP
from virtuals_acp.models import ACPJobPhase
from virtuals_acp.configs import BASE_SEPOLIA_CONFIG
from virtuals_acp import AcpJob
def test_buyer():
    def on_new_task(job: AcpJob, callback: Callable):
        if job.phase == ACPJobPhase.NEGOTIATION:
            # Check if there's a memo that indicates next phase is TRANSACTION
            for memo in job.memos:
                if memo.next_phase == ACPJobPhase.TRANSACTION:
                    print("Paying job", job)
                    job.pay(2)
                    callback(True)
                    break
        elif job.phase == ACPJobPhase.COMPLETED:
            callback(True)
            print("Job completed", job)
            
            
    acp = VirtualsACP(
        wallet_private_key="60e3438e1cd3b3ca6afa310e3350a59fa8a51ba42266c1281dee237b8ec264f2",
        agent_wallet_address="0x9cb1497E8192FDCc60c4dC6D3B01F40D9215ad50",
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
