import os
import sys
from typing import Optional
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from pydantic import BaseModel, field_validator
from models import MemoType, ACPJobPhase
class AcpMemo(BaseModel):
    id: int
    type: MemoType 
    content: str
    next_phase: int
    
    class Config:
        arbitrary_types_allowed = True
