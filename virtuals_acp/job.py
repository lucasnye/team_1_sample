from typing import List, Optional
from .client import VirtualsACP
from .models import ACPJobPhase
from .memo import AcpMemo

class AcpJob:
    def __init__(
        self,
        acp_client: VirtualsACP,
        id: int,
        provider_address: str,
        memos: List[AcpMemo],
        phase: ACPJobPhase
    ):
        self.acp_client = acp_client
        self.id = id
        self.provider_address = provider_address
        self.memos = memos
        self.phase = phase

    def pay(self, amount: int, reason: Optional[str] = None):
        memo = next(
            (m for m in self.memos if m.next_phase == ACPJobPhase.TRANSACTION),
            None
        )

        if not memo:
            raise ValueError("No transaction memo found")

        return  self.acp_client.pay_job(self.id, amount, memo.id, reason)

    def respond(self, accept: bool, reason: Optional[str] = None):
        memo = next(
            (m for m in self.memos if m.next_phase == ACPJobPhase.NEGOTIATION),
            None
        )

        if not memo:
            raise ValueError("No negotiation memo found")

        return self.acp_client.respond_job(self.id, memo.id, accept, reason)

    def deliver(self, deliverable: str):
        memo = next(
            (m for m in self.memos if m.next_phase == ACPJobPhase.EVALUATION),
            None
        )

        if not memo:
            raise ValueError("No transaction memo found")

        return self.acp_client.deliver_job(self.id, deliverable)

    def evaluate(self, accept: bool, reason: Optional[str] = None):
        memo = next(
            (m for m in self.memos if m.next_phase == ACPJobPhase.COMPLETED),
            None
        )

        if not memo:
            raise ValueError("No evaluation memo found")

        return self.acp_client.contract_manager.sign_memo(
            memo.id,
            accept,
            reason
        )
