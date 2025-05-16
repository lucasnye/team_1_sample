import os
import sys

from typing import Optional, List
from ..models import ACPJobPhase
from ..client import VirtualsACP

def get_memo_for_phase(memos: List, phase: ACPJobPhase):
    return next((m for m in memos if ACPJobPhase(m.next_phase) == phase), None)

def respond_job(acp: VirtualsACP, job_id: int, memos: List, accept: bool, reason: Optional[str] = None):
    memo = get_memo_for_phase(memos, ACPJobPhase.NEGOTIATION)
    if not memo:
        raise ValueError("No negotiation memo found")
    
    if not reason:
        reason = f"Job {job_id} accepted. {reason if reason else ''}"
        
    return acp.respond_to_job_memo(job_id, memo.id, accept, reason)

def pay_job(acp: VirtualsACP, job_id: int, memos: List, amount: int, reason: Optional[str] = None):
    memo = get_memo_for_phase(memos, ACPJobPhase.TRANSACTION)
    
    if not memo:
        raise ValueError("No transaction memo found")
    
    if not reason:
        reason = f"Job {job_id} paid. {reason if reason else ''}"
        
    return acp.pay_for_job(job_id, memo.id, amount, reason)

def deliver_job(acp: VirtualsACP, job_id: int, memos: List, deliverable: str):
    memo = get_memo_for_phase(memos, ACPJobPhase.EVALUATION)
    
    if not memo:
        raise ValueError("No evaluation memo found")
    
    return acp.submit_job_deliverable(job_id, deliverable)

def evaluate_job(acp: VirtualsACP, memos: List, accept: bool, reason: Optional[str] = None):
    memo = get_memo_for_phase(memos, ACPJobPhase.COMPLETED)
    if not memo:
        raise ValueError("No evaluation memo found")
    return acp.evaluate_job_delivery(memo.id, accept, reason)
