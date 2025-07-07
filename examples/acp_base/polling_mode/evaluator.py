import time
from typing import List

from dotenv import load_dotenv

from virtuals_acp import VirtualsACP, ACPJob, ACPJobPhase
from virtuals_acp.env import EnvSettings

load_dotenv(override=True)

# --- Configuration for the job polling interval ---
POLL_INTERVAL_SECONDS = 20


# --------------------------------------------------

def evaluator():
    env = EnvSettings()

    acp = VirtualsACP(
        wallet_private_key=env.WHITELISTED_WALLET_PRIVATE_KEY,
        agent_wallet_address=env.EVALUATOR_AGENT_WALLET_ADDRESS,
        entity_id=env.EVALUATOR_ENTITY_ID,
    )
    print(f"Evaluator ACP Initialized. Agent: {acp.agent_address}")

    evaluated_deliverables = set()  # Store (job_id, deliverable_memo_id) to avoid re-evaluation

    while True:
        print(f"\nEvaluator: Polling for jobs assigned to {acp.agent_address} requiring evaluation...")
        active_jobs_list: List[ACPJob] = acp.get_active_jobs()

        if not active_jobs_list:
            print("Evaluator: No active jobs found in this poll.")
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        for job_summary in active_jobs_list:
            onchain_job_id = job_summary.id

            try:
                job = acp.get_job_by_onchain_id(onchain_job_id)
                current_phase = job.phase

                # Ensure this job is for the current evaluator
                if job.evaluator_address != acp.agent_address:
                    continue

                if current_phase == ACPJobPhase.EVALUATION:
                    print(f"Evaluator: Found Job {onchain_job_id} in EVALUATION phase.")

                    # Find the seller's deliverable memo. Its next_phase should be COMPLETED.
                    seller_deliverable_memo_to_sign = None
                    for memo in reversed(job.memos):  # Check latest first
                        if ACPJobPhase(memo.next_phase) == ACPJobPhase.COMPLETED:
                            seller_deliverable_memo_to_sign = memo
                            break

                    if seller_deliverable_memo_to_sign:
                        deliverable_key = (onchain_job_id, seller_deliverable_memo_to_sign.id)
                        if deliverable_key in evaluated_deliverables:
                            print(
                                f"Deliverable memo {seller_deliverable_memo_to_sign.id} for job {onchain_job_id} already processed.")
                            continue

                        print(
                            f"  Job {onchain_job_id}: Found deliverable memo {seller_deliverable_memo_to_sign.id} to evaluate.")
                        print(f"  Deliverable Content: {seller_deliverable_memo_to_sign.content}")

                        # Simple evaluation logic: always accept
                        accept_the_delivery = True
                        evaluation_reason = "Deliverable looks great, approved!"

                        print(f"  Job {onchain_job_id}: Evaluating... Accepting: {accept_the_delivery}")
                        acp.evaluate_job_delivery(
                            memo_id_of_deliverable=seller_deliverable_memo_to_sign.id,
                            accept=accept_the_delivery,
                            reason=evaluation_reason
                        )
                        print(
                            f"  Job {onchain_job_id}: Evaluation submitted for memo {seller_deliverable_memo_to_sign.id}.")
                        evaluated_deliverables.add(deliverable_key)
                    else:
                        print(
                            f"  Job {onchain_job_id} in EVALUATION, but no deliverable memo (next_phase=COMPLETED) found yet.")
                elif current_phase in [ACPJobPhase.REQUEST, ACPJobPhase.NEGOTIATION]:
                    print(
                        f"Evaluator: Job {onchain_job_id} is in {current_phase.name} phase. Waiting for job to be delivered.")
                    continue
                elif current_phase in [ACPJobPhase.COMPLETED, ACPJobPhase.REJECTED]:
                    print(f"Evaluator: Job {onchain_job_id} is already in {current_phase.name}. No action.")

            except Exception as e:
                print(f"Evaluator: Error processing job {onchain_job_id}: {e}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    evaluator()
