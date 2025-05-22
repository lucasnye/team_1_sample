from typing import Optional, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict
from virtuals_acp.models import MemoType
from virtuals_acp.models import ACPJobPhase


class ACPMemo(BaseModel):
    id: int
    type: MemoType 
    content: str
    next_phase: ACPJobPhase
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __str__(self):
        return f"AcpMemo(id={self.id}, type={self.type}, content={self.content}, next_phase={self.next_phase})"

