import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from models import MemoType

class AcpMemo:
    def __init__(
        self,
        id: int,
        type: MemoType,
        content: str,
        next_phase: int
    ):
        self.id = id
        self.type = type
        self.content = content
        self.next_phase = next_phase
