# virtuals_acp/models.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class MemoType(Enum):
    MESSAGE = 0
    CONTEXT_URL = 1
    IMAGE_URL = 2
    VOICE_URL = 3
    OBJECT_URL = 4
    TXHASH = 5

class ACPJobPhase(Enum):
    REQUEST = 0
    NEGOTIATION = 1
    TRANSACTION = 2
    EVALUATION = 3
    COMPLETED = 4
    REJECTED = 5

@dataclass
class ACPMemo:
    id: int
    job_id: int
    sender_address: str
    type: MemoType
    content: str
    next_phase: ACPJobPhase
    is_secured: bool
    # raw_data: Dict[str, Any] # To store the full memo data from contract if needed

@dataclass
class ACPJob:
    id: int
    client_address: str
    provider_address: str
    evaluator_address: str
    budget: int  # in wei
    amount_claimed: int # in wei
    phase: ACPJobPhase
    memo_count: int
    expired_at_timestamp: int
    memos: List[ACPMemo] = field(default_factory=list)
    # raw_data: Dict[str, Any] # To store the full job data from contract


# should this be description and price and maybe rename it to ACP Task?
@dataclass
class ACPOffering:
    name: str
    price: float # Assuming price is a float, adjust if it's wei or other format

# class and datastructure returned from the Virtuals ACP Agent Registry
@dataclass
class ACPAgent:
    id: int
    name: str
    description: str
    wallet_address: str # Checksummed address
    offerings: List[ACPOffering] = field(default_factory=list)
    twitter_handle: Optional[str] = None
    # Full fields from TS for completeness, though browse_agent returns a subset
    document_id: Optional[str] = None
    is_virtual_agent: Optional[bool] = None
    profile_pic: Optional[str] = None
    category: Optional[str] = None
    token_address: Optional[str] = None
    owner_address: Optional[str] = None
    cluster: Optional[str] = None
    symbol: Optional[str] = None
    virtual_agent_id: Optional[str] = None


