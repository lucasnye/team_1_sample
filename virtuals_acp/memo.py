from typing import Optional
from .client import VirtualsACP
from .models import MemoType

class AcpMemo:
    def __init__(
        self,
        acp_client: VirtualsACP,
        id: int,
        type: MemoType,
        content: str,
        next_phase: int
    ):
        self.acp_client = acp_client
        self.id = id
        self.type = type
        self.content = content
        self.next_phase = next_phase

    async def create(self, job_id: int, is_secured: bool = True):
        return await self.acp_client.contract_manager.create_memo(
            self.acp_client.agent_address,
            job_id,
            self.content,
            self.type,
            is_secured,
            self.next_phase
        )

    async def sign(self, approved: bool, reason: Optional[str] = None):
        return await self.acp_client.contract_manager.sign_memo(
            self.id,
            approved,
            reason
        )
