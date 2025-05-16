import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import ACPJobPhase
from typing import Optional, List
from client import VirtualsACP

def get_memo_for_phase(memos: List, phase: ACPJobPhase):
    return next((m for m in memos if m.next_phase == phase), None)

def respond_job(acp: VirtualsACP, job_id: int, memos: List, accept: bool, reason: Optional[str] = None):
    memo = get_memo_for_phase(memos, ACPJobPhase.NEGOTIATION)
    if not memo:
        raise ValueError("No negotiation memo found")
    return acp.respond_job(job_id, memo.id, accept, reason)

def pay_job(acp: VirtualsACP, job_id: int, memos: List, amount: int, reason: Optional[str] = None):
    memo = get_memo_for_phase(memos, ACPJobPhase.TRANSACTION)
    if not memo:
        raise ValueError("No transaction memo found")
    return acp.pay_job(job_id, amount, memo.id, reason)

def deliver_job(acp: VirtualsACP, job_id: int, memos: List, deliverable: str):
    memo = get_memo_for_phase(memos, ACPJobPhase.EVALUATION)
    if not memo:
        raise ValueError("No evaluation memo found")
    return acp.deliver_job(job_id, deliverable)

def evaluate_job(acp: VirtualsACP, memos: List, accept: bool, reason: Optional[str] = None):
    memo = get_memo_for_phase(memos, ACPJobPhase.COMPLETED)
    if not memo:
        raise ValueError("No evaluation memo found")
    return acp.contract_manager.sign_memo(memo.id, accept, reason)
