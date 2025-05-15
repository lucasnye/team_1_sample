import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from memo import AcpMemo
from client import VirtualsACP

async def create_memo(acp_client: VirtualsACP, memo: AcpMemo, job_id: int, is_secured: bool = True):
    return await acp_client.contract_manager.create_memo(
        acp_client.agent_address,
        job_id,
        memo.content,
        memo.type,
        is_secured,
        memo.next_phase
    )

async def sign_memo(acp_client: VirtualsACP, memo: AcpMemo, approved: bool, reason: str = None):
    return await acp_client.contract_manager.sign_memo(
        memo.id,
        approved,
        reason
    )
