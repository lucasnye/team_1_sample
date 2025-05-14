# virtuals_acp/client.py

import requests
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Union, Dict, Any
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount

# Relative imports within the package
from .configs import ACPContractConfig, DEFAULT_CONFIG
from .models import ACPAgent, ACPJobPhase, MemoType, ACPOffering, ACPJob
from .exceptions import ACPApiError, ACPContractError, ACPError
from .contract_manager import _ACPContractManager # Import the refactored class

class VirtualsACP:
    def __init__(self, 
                 wallet_private_key: str, 
                 agent_wallet_address: Optional[str] = None, 
                 config: Optional[ACPContractConfig] = DEFAULT_CONFIG):
        
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url))

        if config.chain_env == "base-sepolia":
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC URL: {config.rpc_url}")

        self.signer_account: LocalAccount = Account.from_key(wallet_private_key)
        
        if agent_wallet_address:
            self._agent_wallet_address = Web3.to_checksum_address(agent_wallet_address)
        else:
            self._agent_wallet_address = self.signer_account.address
            # print(f"Warning: agent_wallet_address not provided, defaulting to signer EOA: {self._agent_wallet_address}")

        # Initialize the contract manager here
        self.contract_manager = _ACPContractManager(self.w3, self.signer_account, config)
        self.acp_api_url = config.acp_api_url
        
    @property
    def agent_address(self) -> str:
        return self._agent_wallet_address

    @property
    def signer_address(self) -> str:
        return self.signer_account.address

    def browse_agents(self, keyword: str, cluster: Optional[str] = None) -> List[ACPAgent]:
        url = f"{self.acp_api_url}/agents?search={keyword}&filters[walletAddress][$neq]={self.agent_address}"
        if cluster:
            url += f"&filters[cluster]={cluster}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            agents_data = data.get("data", [])
            agents = []
            for agent_data in agents_data:
                offerings = [
                    ACPOffering(name=off["name"], price=off["price"])
                    for off in agent_data.get("offerings", [])
                ]
                agents.append(ACPAgent(
                    id=agent_data["id"],
                    name=agent_data.get("name"),
                    description=agent_data.get("description"),
                    wallet_address=Web3.to_checksum_address(agent_data["walletAddress"]),
                    offerings=offerings,
                    twitter_handle=agent_data.get("twitterHandle")
                ))
            return agents
        except requests.exceptions.RequestException as e:
            raise ACPApiError(f"Failed to browse agents: {e}")
        except Exception as e:
            raise ACPError(f"An unexpected error occurred while browsing agents: {e}")

    def initiate_job(
        self,
        provider_address: str,
        service_requirement: str,
        expired_at: Optional[datetime] = None,
        evaluator_address: Optional[str] = None
    ) -> int:
        if expired_at is None:
            expired_at = datetime.now(timezone.utc) + timedelta(days=1)
        
        eval_addr = Web3.to_checksum_address(evaluator_address) if evaluator_address else self.agent_address

        tx_hash, job_id = self.contract_manager.create_job(
            provider_address, eval_addr, expired_at
        )
        # print(f"Job creation tx: {tx_hash}, Job ID: {job_id}, initiated by signer {self.signer_address} for agent {self.agent_address}")

        self.contract_manager.create_memo(
            job_id,
            service_requirement,
            MemoType.MESSAGE,
            is_secured=True,
            next_phase=ACPJobPhase.NEGOTIATION
        )
        # print(f"Initial memo for job {job_id} created.")
        return job_id

    def respond_to_job_memo(self, memo_id: int, accept: bool, reason: Optional[str] = "") -> str:
        tx_hash = self.contract_manager.sign_memo(memo_id, accept, reason or "")
        # print(f"Response (signMemo) tx: {tx_hash} for memo ID {memo_id}")
        return tx_hash

    def pay_for_job(self, job_id: int, amount_in_eth: Union[float, str]) -> Tuple[str, str]:
        amount_in_wei = self.w3.to_wei(amount_in_eth, "ether")
        
        approve_tx_hash = self.contract_manager.approve_allowance(amount_in_wei)
        # print(f"Token approval tx: {approve_tx_hash} for job {job_id}")

        set_budget_tx_hash = self.contract_manager.set_budget(job_id, amount_in_wei)
        # print(f"Set budget tx: {set_budget_tx_hash} for job {job_id}")
        
        return approve_tx_hash, set_budget_tx_hash

    def submit_job_deliverable(self, job_id: int, deliverable_content: str, deliverable_type: MemoType = MemoType.OBJECT_URL) -> str:
        tx_hash = self.contract_manager.create_memo(
            job_id,
            deliverable_content,
            deliverable_type,
            is_secured=True, 
            next_phase=ACPJobPhase.COMPLETED 
        )
        # print(f"Deliverable submission tx: {tx_hash} for job {job_id}")
        return tx_hash

    def evaluate_job_delivery(self, memo_id_of_deliverable: int, accept: bool, reason: Optional[str] = "") -> str:
        tx_hash = self.contract_manager.sign_memo(memo_id_of_deliverable, accept, reason or "")
        # print(f"Evaluation (signMemo) tx: {tx_hash} for deliverable memo ID {memo_id_of_deliverable}")
        return tx_hash

    def get_job_details(self, job_id: int) -> ACPJob:
        return self.contract_manager.get_job_details(job_id)

    def get_active_jobs(self) -> List[ACPJob]:
        # print("get_active_jobs: Not fully implemented, requires event querying or backend.")
        return [] # Placeholder

    def get_job_memos(self, job_id: int, phase: Optional[ACPJobPhase] = None, offset: int = 0, limit: int = 10) -> Tuple[List[Dict[str, Any]], int]:
        try:
            if phase:
                raw_memos, total = self.contract_manager.contract.functions.getMemosForPhase(
                    job_id, phase.value, offset, limit
                ).call()
            else:
                raw_memos, total = self.contract_manager.contract.functions.getAllMemos(
                    job_id, offset, limit
                ).call()
            
            memos = []
            for raw_memo_tuple in raw_memos:
                # Structure from ABI: (content, memoType, isSecured, nextPhase, jobId, sender)
                memos.append({
                    "content": raw_memo_tuple[0],
                    "memo_type": MemoType(raw_memo_tuple[1]),
                    "is_secured": raw_memo_tuple[2],
                    "next_phase": ACPJobPhase(raw_memo_tuple[3]),
                    # "job_id_in_memo": raw_memo_tuple[4], # Redundant if called with job_id
                    "sender": raw_memo_tuple[5],
                    # "id": "UNKNOWN" # Memo ID is crucial and not returned by these view functions
                                     # This is a limitation of the current smart contract view functions
                                     # Typically, memo IDs are obtained from NewMemo events.
                })
            return memos, total
        except Exception as e:
            raise ACPContractError(f"Failed to get memos for job {job_id}: {e}")