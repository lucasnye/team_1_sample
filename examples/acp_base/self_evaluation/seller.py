import os
import threading
import time
from collections import deque
from typing import Optional

from dotenv import load_dotenv

# -----------------------------
# 1) Load .env and HARD-OVERRIDE to Sepolia
# -----------------------------
load_dotenv(override=True)

# Force Sepolia env for this process (cannot be overridden by defaults)
os.environ["CHAIN_ENV"] = "base-sepolia"
os.environ["CHAIN_ID"] = "84532"

# If you already have a Sepolia RPC in .env it will be used; otherwise fallback here.
if not os.getenv("RPC_URL"):
    os.environ["RPC_URL"] = "https://base-sepolia.g.alchemy.com/v2/<YOUR_API_KEY>"
os.environ["BASE_SEPOLIA_RPC_URL"] = os.environ["RPC_URL"]

# Nuke possible mainnet fallbacks some SDK builds sniff
for k in ("BASE_MAINNET_RPC_URL", "MAINNET_RPC_URL", "BASE_RPC_URL"):
    os.environ.pop(k, None)

from virtuals_acp import VirtualsACP, ACPJob, ACPJobPhase, ACPMemo, IDeliverable
from virtuals_acp.env import EnvSettings


def seller(use_thread_lock: bool = True):
    env = EnvSettings()

    # -----------------------------
    # Debug what the SDK actually read
    # -----------------------------
    print("DEBUG CHAIN_ENV :", getattr(env, "CHAIN_ENV", None))
    print("DEBUG CHAIN_ID  :", getattr(env, "CHAIN_ID", None))
    print("DEBUG RPC_URL   :", getattr(env, "RPC_URL", None) or getattr(env, "BASE_SEPOLIA_RPC_URL", None))
    print("DEBUG ACP_API_URL:", getattr(env, "ACP_API_URL", None))

    if env.WHITELISTED_WALLET_PRIVATE_KEY is None:
        raise ValueError("WHITELISTED_WALLET_PRIVATE_KEY is not set")
    if env.SELLER_AGENT_WALLET_ADDRESS is None:
        raise ValueError("SELLER_AGENT_WALLET_ADDRESS is not set")
    if env.SELLER_ENTITY_ID is None:
        raise ValueError("SELLER_ENTITY_ID is not set")

    job_queue = deque()
    job_queue_lock = threading.Lock()
    job_event = threading.Event()

    def safe_append_job(job, memo_to_sign: Optional[ACPMemo] = None):
        if use_thread_lock:
            print(f"[safe_append_job] Acquiring lock to append job {job.id}")
            with job_queue_lock:
                print(f"[safe_append_job] Lock acquired, appending job {job.id} to queue")
                job_queue.append((job, memo_to_sign))
        else:
            job_queue.append((job, memo_to_sign))

    def safe_pop_job():
        if use_thread_lock:
            print(f"[safe_pop_job] Acquiring lock to pop job")
            with job_queue_lock:
                if job_queue:
                    job, memo_to_sign = job_queue.popleft()
                    print(f"[safe_pop_job] Lock acquired, popped job {job.id}")
                    return job, memo_to_sign
                else:
                    print("[safe_pop_job] Queue is empty after acquiring lock")
        else:
            if job_queue:
                job, memo_to_sign = job_queue.popleft()
                print(f"[safe_pop_job] Popped job {job.id} without lock")
                return job, memo_to_sign
            else:
                print("[safe_pop_job] Queue is empty (no lock)")
        return None, None

    def job_worker():
        while True:
            job_event.wait()
            while True:
                job, memo_to_sign = safe_pop_job()
                if not job:
                    break
                threading.Thread(target=handle_job_with_delay, args=(job, memo_to_sign), daemon=True).start()
            if use_thread_lock:
                with job_queue_lock:
                    if not job_queue:
                        job_event.clear()
            else:
                if not job_queue:
                    job_event.clear()

    def handle_job_with_delay(job, memo_to_sign):
        try:
            process_job(job, memo_to_sign)
            time.sleep(2)
        except Exception as e:
            print(f"❌ Error processing job: {e}")

    def on_new_task(job: ACPJob, memo_to_sign: Optional[ACPMemo] = None):
        print(f"[on_new_task] Received job {job.id} (phase: {job.phase})")
        safe_append_job(job, memo_to_sign)
        job_event.set()

    def process_job(job: ACPJob, memo_to_sign: Optional[ACPMemo] = None):
        if (
            job.phase == ACPJobPhase.REQUEST and
            memo_to_sign is not None and
            memo_to_sign.next_phase == ACPJobPhase.NEGOTIATION
        ):
            job.respond(True)
        elif (
            job.phase == ACPJobPhase.TRANSACTION and
            memo_to_sign is not None and
            memo_to_sign.next_phase == ACPJobPhase.EVALUATION
        ):
            print(f"Delivering job {job.id}")
            deliverable = IDeliverable(type="url", value="https://example.com")
            job.deliver(deliverable)
        elif job.phase == ACPJobPhase.COMPLETED:
            print("Job completed", job)
        elif job.phase == ACPJobPhase.REJECTED:
            print("Job rejected", job)

    threading.Thread(target=job_worker, daemon=True).start()

    # Initialize the ACP client (now guaranteed to use Sepolia)
    VirtualsACP(
        wallet_private_key=env.WHITELISTED_WALLET_PRIVATE_KEY,
        agent_wallet_address=env.SELLER_AGENT_WALLET_ADDRESS,
        on_new_task=on_new_task,
        entity_id=env.SELLER_ENTITY_ID
    )

    print("Waiting for new task...")
    threading.Event().wait()


if __name__ == "__main__":
    seller()
