import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from typing import List
from models import ACPJobPhase
from memo import AcpMemo

class AcpJob:
    def __init__(
        self,
        id: int,
        provider_address: str,
        memos: List[AcpMemo],
        phase: ACPJobPhase
    ):
        self.id = id
        self.provider_address = provider_address
        self.memos = memos
        self.phase = phase
