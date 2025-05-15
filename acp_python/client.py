# virtuals_acp/client.py

import json
import traceback
from wsgiref import validate
from jsonschema import ValidationError
import requests
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Union, Dict, Any
from web3 import Web3
from web3.middleware.geth_poa import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount
import socketio
import socketio.client

from utils.job_helpers import build_acp_job
from .memo import AcpMemo
from .models import  ACPJobPhase, IACPJob, MemoType, IACPAgent

# Relative imports within the package
from .configs import ACPContractConfig, DEFAULT_CONFIG
from .exceptions import ACPApiError, ACPContractError, ACPError
from .contract_manager import _ACPContractManager # Import the refactored class

class VirtualsACP:
    def __init__(self, 
                 wallet_private_key: str, 
                 agent_wallet_address: Optional[str] = None, 
                 config: Optional[ACPContractConfig] = DEFAULT_CONFIG,
                 on_new_task: Optional[callable] = None,
                 on_evaluate: Optional[callable] = None):
        
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
        self.contract_manager = _ACPContractManager(self.w3, config, wallet_private_key)
        self.acp_api_url = config.acp_api_url
        
        # Socket.IO setup
        self.on_new_task = on_new_task
        self.on_evaluate = on_evaluate or self._default_on_evaluate
        self.sio = socketio.Client()
        self._setup_socket_handlers()
        self._connect_socket()

    def _default_on_evaluate(self, job: IACPJob) -> Tuple[bool, str]:
        """Default handler for job evaluation events."""
        return True,"Succesful"

    def _setup_socket_handlers(self) -> None:
        """Set up socket event handlers."""
        @self.sio.on('roomJoined')
        def on_room_joined(data):
            print('Connected to room',data)
            
        @self.sio.on('onEvaluate')
        def handle_evaluate(data):
            if self.on_evaluate:
                job = build_acp_job(self, data)
                self.on_evaluate(job)

        @self.sio.on('onNewTask')
        def handle_new_task(data):
            print("on_new_task", data)
            if self.on_new_task:
                job = build_acp_job(data)
                self.on_new_task(job)

    def _connect_socket(self) -> None:
        """Connect to the socket server with appropriate authentication."""
        auth_data = {}
        if self.on_new_task:
            auth_data['walletAddress'] = self.agent_address
            
        if self.on_evaluate != self._default_on_evaluate:
            auth_data['evaluatorAddress'] = self.agent_address

        print(auth_data)
        try:
            self.sio.connect(
                self.acp_api_url,
                auth=auth_data,
            )
            
        except Exception as e:
            print(f"Failed to connect to socket server: {e}")

    def disconnect(self) -> None:
        """Disconnect from the socket server."""
        if self.sio.connected:
            self.sio.disconnect()

    def __del__(self):
        """Cleanup when the object is destroyed."""
        self.disconnect()

    @property
    def agent_address(self) -> str:
        return self._agent_wallet_address

    @property
    def signer_address(self) -> str:
        return self.signer_account.address

    def browse_agents(self, keyword: str, cluster: Optional[str] = None) -> List[IACPAgent]:
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
                    AcpJobOffering(
                        acp_client=self,
                        provider_address=agent_data["walletAddress"],
                        type=off["name"],
                        price=off["price"],
                        schema=off.get("schema", None)
                    )
                    for off in agent_data.get("offerings", [])
                ]
                
                agents.append(IACPAgent(
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
        price: float,
        provider_address: str,
        service_requirement: str | Dict[str, Any],
        expired_at: Optional[datetime] = None,
        evaluator_address: Optional[str] = None,
    ) -> int:
        if expired_at is None:
            expired_at = datetime.now(timezone.utc) + timedelta(days=1)
        
        eval_addr = Web3.to_checksum_address(evaluator_address) if evaluator_address else self.agent_address
        
        job_id = None
        retry_count = 3
        retry_delay = 3
        
        tx_hash = self.contract_manager.create_job(
            self.agent_address, provider_address, eval_addr, expired_at
        )
        # print(f"Job creation tx: {tx_hash}, Job ID: {job_id}, initiated by signer {self.signer_address} for agent {self.agent_address}")

        time.sleep(retry_delay) 
        for attempt in range(retry_count):
            try:
                response = self.contract_manager.validate_transaction(tx_hash['txHash'])
                data = response.get("data", {})
                if not data:
                    raise Exception("Invalid tx_hash!")
                
                if (data.get("status") == "retry"):
                    raise Exception("Transaction failed, retrying...")
                
                if (data.get("status") == "failed"):
                    break
                
                if (data.get("status") == "success"):
                    job_id = int(data.get("result").get("jobId"))
                    
                if (job_id is not None and job_id != ""):
                    break  
                
            except Exception as e:
                print(f"Error in create_job function: {e}")
                print(traceback.format_exc())
                if attempt < retry_count - 1:
                    time.sleep(retry_delay) 
                else:
                    raise
        
        if (job_id is None or job_id == ""):
            raise Exception("Failed to create job")
        
        self.contract_manager.create_memo(
            self.agent_address,
            job_id,
            service_requirement if isinstance(service_requirement, str) else json.dumps(service_requirement),
            MemoType.MESSAGE,
            is_secured=True,
            next_phase=ACPJobPhase.NEGOTIATION
        )
        print(f"Initial memo for job {job_id} created.")
        
        payload = {
            "jobId": job_id,
            "clientAddress": self.agent_address,
            "providerAddress": provider_address,
            "description": service_requirement,
            "price": price,
            "expiredAt": expired_at.astimezone(timezone.utc).isoformat(),
            "evaluatorAddress": evaluator_address
        }
        
        requests.post(
            self.acp_api_url,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        return job_id

    def respond_to_job_memo(self, memo_id: int, accept: bool, reason: Optional[str] = "") -> str:
        tx_hash = self.contract_manager.sign_memo(self.agent_address, memo_id, accept, reason or "")
        # print(f"Response (signMemo) tx: {tx_hash} for memo ID {memo_id}")
        return tx_hash

    def pay_for_job(self, job_id: int, amount_in_eth: Union[float, str]) -> Tuple[str, str]:
        amount_in_wei = self.w3.to_wei(amount_in_eth, "ether")
        
        approve_tx_hash = self.contract_manager.approve_allowance(self.agent_address, amount_in_wei)
        # print(f"Token approval tx: {approve_tx_hash} for job {job_id}")

        set_budget_tx_hash = self.contract_manager.set_budget(self.agent_address, job_id, amount_in_wei)
        # print(f"Set budget tx: {set_budget_tx_hash} for job {job_id}")
        
        return approve_tx_hash, set_budget_tx_hash

    def submit_job_deliverable(self, job_id: int, deliverable_content: str, deliverable_type: MemoType = MemoType.OBJECT_URL) -> str:
        tx_hash = self.contract_manager.create_memo(
            self.agent_address,
            job_id,
            deliverable_content,
            deliverable_type,
            is_secured=True, 
            next_phase=ACPJobPhase.COMPLETED 
        )
        # print(f"Deliverable submission tx: {tx_hash} for job {job_id}")
        return tx_hash

    def evaluate_job_delivery(self, memo_id_of_deliverable: int, accept: bool, reason: Optional[str] = "") -> str:
        tx_hash = self.contract_manager.sign_memo(self.agent_address, memo_id_of_deliverable, accept, reason or "")
        # print(f"Evaluation (signMemo) tx: {tx_hash} for deliverable memo ID {memo_id_of_deliverable}")
        return tx_hash

    def get_job_details(self, job_id: int) -> AcpJob:
        return self.contract_manager.get_job_details(job_id)

    def get_active_jobs(self) -> List[AcpJob]:
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
class AcpJobOffering:
    def __init__(
        self,
        acp_client: VirtualsACP,
        provider_address: str,
        type: str,
        price: float,
        schema: str
    ):
        self.acp_client = acp_client
        self.provider_address = provider_address
        self.type = type
        self.price = price
        try:
            self.schema = json.loads(schema) if schema else None
        except json.JSONDecodeError:
            self.schema = None

    def initiate_job(
        self,
        price: float,
        service_requirement: Union[Dict[str, Any], str],
        expired_at: datetime
    ) -> int:
        if self.schema:
            try:
                # If service_requirement is a string, parse it as JSON
                if isinstance(service_requirement, str):
                    service_requirement = json.loads(service_requirement)
                
                validate(instance=service_requirement, schema=self.schema)
            except ValidationError as e:
                raise ValueError(f"Invalid service requirement: {str(e)}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in service requirement: {str(e)}")
        return  self.acp_client.initiate_job(
            price,
            self.provider_address,
            service_requirement,
            expired_at
        )