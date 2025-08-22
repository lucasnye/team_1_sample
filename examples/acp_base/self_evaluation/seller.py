import threading
import time
from collections import deque
from typing import Optional
import json
from parser import parse_proposal
from report import *
from markdown_pdf import MarkdownPdf, Section
import requests
import boto3
import os


from dotenv import load_dotenv

from virtuals_acp import VirtualsACP, ACPJob, ACPJobPhase, ACPMemo, IDeliverable
from virtuals_acp.env import EnvSettings

load_dotenv(override=True)


def upload_pdf_to_s3(file_path, bucket_name, object_name, aws_access_key, aws_secret_key, region="ap-southeast-1"):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=region
    )
    s3.upload_file(file_path, bucket_name, object_name)
    url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_name}"
    return url

def seller(use_thread_lock: bool = True):
    env = EnvSettings()

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
                # Process each job in its own thread to avoid blocking
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
            print(f"\u274c Error processing job: {e}")

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

            buyer_text = job.service_requirement.get("Company Name", "")
            startup = parse_proposal(buyer_text)
            context = {
                "peer_companies": [
                    {
                        "company_name": "MedFlow",
                        "industry": "HealthTech",
                        "subsector": "Clinic Management",
                        "stage": "Series A",
                        "hq_location": "Boston, MA",
                        "business_model": "B2B SaaS",
                        "markets": ["North America"],
                        "moat": "Exclusive partnerships with major EHR providers",
                        "go_to_market": "Channel partners and medical distributors",
                        "tech_stack": ["Java", "React", "MongoDB"],
                        "description": "End-to-end clinic management suite with integrated billing.",
                        "keywords": ["clinic SaaS", "EHR", "workflow"],
                        "profitability": "not yet profitable",
                        "growth_rate": 0.25
                    },
                    {
                        "company_name": "ClinicAI",
                        "industry": "HealthTech",
                        "subsector": "Patient Engagement",
                        "stage": "Series B",
                        "hq_location": "New York, NY",
                        "business_model": "B2B SaaS",
                        "markets": ["North America", "Asia"],
                        "moat": "First-mover advantage with regulatory certifications",
                        "go_to_market": "Hybrid inbound and outbound sales",
                        "description": "Automated patient follow-up and appointment scheduling.",
                        "keywords": ["patient engagement", "automation", "health SaaS"],
                        "profitability": "break-even",
                        "growth_rate": 0.3
                    }
                ]
            }
            generated_report = generate_report(startup, context)
            pdf = MarkdownPdf(toc_level=2, optimize=True)
            section = Section(generated_report) # Pass your report text as the first argument
            pdf.add_section(section)
            pdf.save("Profitability_Report.pdf")

            pdf_url = upload_pdf_to_s3(
                "Profitability_Report.pdf",
                bucket_name="virtualsprotocolbucket",
                object_name=f"reports/Profitability_Report_{job.id}.pdf",
                aws_access_key="AKIAWMJELNR7KPAPQQ62",
                aws_secret_key=os.getenv("AWS_SECRET_KEY"),
                region="ap-southeast-1"  # <-- Set your bucket's region here
            )

            deliverable = IDeliverable(
                type="String",
                value=f"Report generated. Download PDF: {pdf_url}\n\n{generated_report}"
            )
            job.deliver(deliverable)
        elif job.phase == ACPJobPhase.COMPLETED:
            print("Job completed", job)
        elif job.phase == ACPJobPhase.REJECTED:
            print("Job rejected", job)

    threading.Thread(target=job_worker, daemon=True).start()

    # Initialize the ACP client
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
