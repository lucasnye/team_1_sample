import os
import sys
from typing import Optional, TYPE_CHECKING
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from pydantic import BaseModel, ConfigDict
from models import MemoType
from acp_sdk.models import ACPJobPhase


class AcpMemo(BaseModel):
    id: int
    type: MemoType 
    content: str
    next_phase: ACPJobPhase
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __str__(self):
        return f"AcpMemo(id={self.id}, type={self.type}, content={self.content}, next_phase={self.next_phase})"

