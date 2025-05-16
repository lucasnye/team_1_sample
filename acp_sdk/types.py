"""Type definitions to avoid circular imports"""
from typing import Protocol, List, Optional, Any, Dict, Union

class VirtualsACPProtocol(Protocol):
    """Protocol class for VirtualsACP to avoid circular imports"""
    async def pay_for_job(self, job_id: int, amount: int) -> Any:
        ...

    async def respond_to_job_memo(self, memo_id: int, accept: bool, reason: Optional[str] = None) -> Any:
        ...

    async def submit_job_deliverable(self, job_id: int, deliverable: str) -> Any:
        ...

    @property
    def agent_address(self) -> str:
        ...

    @property
    def contract_manager(self) -> Any:
        ... 