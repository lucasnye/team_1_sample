# virtuals_acp/__init__.py

from .client import VirtualsACP
from .contract_manager import _ACPContractManager # Usually not public, but if needed for advanced use
from .models import (
    ACPAgent,
    ACPJobPhase,
    MemoType,
    ACPOffering,
    ACPJob,
    ACPMemo
)
from .configs import (
    ACPContractConfig,
    BASE_SEPOLIA_CONFIG,
    BASE_MAINNET_CONFIG,
    DEFAULT_CONFIG
)
from .exceptions import (
    ACPError,
    ACPApiError,
    ACPContractError,
    TransactionFailedError
)
from .abi import ACP_ABI, ERC20_ABI # Export ABI if users might need it directly

__all__ = [
    "VirtualsACP",
    "ACPAgent",
    "ACPJobPhase",
    "MemoType",
    "ACPOffering",
    "ACPJob",
    "ACPMemo",
    "ACPContractConfig",
    "BASE_SEPOLIA_CONFIG",
    "BASE_MAINNET_CONFIG",
    "DEFAULT_CONFIG",
    "ACPError",
    "ACPApiError",
    "ACPContractError",
    "TransactionFailedError",
    "ACP_ABI",
    "ERC20_ABI"
]

__version__ = "0.1.0" # Define your package version here