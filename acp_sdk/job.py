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

    def __str__(self):
        return (
            f"AcpJob(\n"
            f"  id={self.id},\n"
            f"  provider_address='{self.provider_address}',\n"
            f"  memos=[{', '.join(str(memo) for memo in self.memos)}],\n"
            f"  phase={self.phase}\n"
            f")"
        )