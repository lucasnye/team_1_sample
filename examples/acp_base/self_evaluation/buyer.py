from datetime import datetime, timedelta
import time

from acp_sdk import VirtualsACP, ACPJob, ACPJobPhase
from acp_sdk.configs import BASE_SEPOLIA_CONFIG
from acp_sdk.env import EnvSettings

from dotenv import load_dotenv
load_dotenv(override=True)


def test_buyer():
    env = EnvSettings()

    def on_new_task(job: ACPJob):
        if job.phase == ACPJobPhase.NEGOTIATION:
            # Check if there's a memo that indicates next phase is TRANSACTION
            for memo in job.memos:
                if memo.next_phase == ACPJobPhase.TRANSACTION:
                    print("Paying job", job.id)
                    job.pay(2)
                    break
        elif job.phase == ACPJobPhase.COMPLETED:
            print("Job completed", job)
    
    def on_evaluate(job: ACPJob):
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

    agents = acp.browse_agents(keyword="", cluster="")
    print("Agents:", agents)
    job_offering = agents[0].offerings[0]

    job_id = job_offering.initiate_job(
        service_requirement={'Image Description': "Help me to generate a flower meme."},
        expired_at=datetime.now() + timedelta(days=1),
        # evaluator_address=env.BUYER_WALLET_ADDRESS
    )

    print(f"Job {job_id} initiated")

    while True:
        print("Listening for next steps...")
        time.sleep(30)

if __name__ == "__main__":
    test_buyer()
