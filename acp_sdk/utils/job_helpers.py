import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memo import AcpMemo
from job import AcpJob

def build_acp_job(acp_client, data: dict) -> AcpJob:
    """Constructs an AcpJob instance from socket data."""
    memos = [
        AcpMemo(
            memo["memoId"],
            memo["memoType"],
            memo["content"],
            memo["nextPhase"]
        )
        for memo in data.get("memos", [])
    ]

    return AcpJob(
        data["onChainJobId"],
        data["sellerAddress"],
        memos,
        data["phase"]
    )
