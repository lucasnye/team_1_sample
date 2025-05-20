# virtuals_acp/client.py

import json
import traceback
from jsonschema import ValidationError, validate
import requests
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Union, Dict, Any
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from eth_account.signers.local import LocalAccount
import socketio
import socketio.client
from pydantic import BaseModel, field_validator, Field

from acp_sdk.job import AcpJob
import acp_sdk.memo as acp_memo

from acp_sdk.exceptions import ACPApiError, ACPError
from acp_sdk.models import  ACPJobPhase, IACPJob, MemoType, IACPAgent
from acp_sdk.contract_manager import _ACPContractManager
from acp_sdk.configs import ACPContractConfig, DEFAULT_CONFIG


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
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

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
    
    def _on_room_joined(self, data):
        print('Connected to room', data)

    def _on_evaluate(self, data):
        if self.on_evaluate:
            try:
                memos = [acp_memo.AcpMemo(
                    id=memo["memoId"], 
                    type=int(memo["memoType"]),
                    content=memo["content"],
                    next_phase=memo["nextPhase"],
                ) for memo in data["memos"]]
                
                job = AcpJob(
                    acp_client=self,
                    id=data["onChainJobId"],
                    provider_address=data["sellerAddress"],
                    memos=memos,
                    phase=data["phase"]
                )
                self.on_evaluate(job)
            except Exception as e:
                print(f"Error in onEvaluate handler: {e}")

    def _on_new_task(self, data):
        if self.on_new_task:
            print("Received new task:", data["memos"])
            try:
                memos = [acp_memo.AcpMemo(
                    id=memo["memoId"], 
                    type=int(memo["memoType"]),
                    content=memo["content"],
                    next_phase=memo["nextPhase"],
                ) for memo in data["memos"]]
                
                
                job = AcpJob(
                    acp_client=self,
                    id=data["onChainJobId"],
                    provider_address=data["sellerAddress"],
                    memos=memos,
                    phase=ACPJobPhase(int(data["phase"]))
                )
                
                self.on_new_task(job)
            except Exception as e:
                print(f"Error in onNewTask handler: {e}")

    def _setup_socket_handlers(self) -> None:
        self.sio.on('roomJoined', self._on_room_joined)
        self.sio.on('onEvaluate', self._on_evaluate)
        self.sio.on('onNewTask', self._on_new_task)

    def _connect_socket(self) -> None:
        """Connect to the socket server with appropriate authentication."""
        auth_data = {}
        if self.on_new_task:
            auth_data['walletAddress'] = self.agent_address
            
        if self.on_evaluate != self._default_on_evaluate:
            auth_data['evaluatorAddress'] = self.agent_address

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
        url = f"{self.acp_api_url}/agents?search={keyword}&filters[walletAddress][$notIn]={self.agent_address}"
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
                        requirementSchema=off.get("requirementSchema", None)
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
                if (attempt == retry_count - 1):
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

    def respond_to_job_memo(self,job_id: int, memo_id: int, accept: bool, reason: Optional[str] = "") -> str:
        try:
            tx_hash = self.contract_manager.sign_memo(self.agent_address, memo_id, accept, reason or "")
            
            time.sleep(10)
            
            print(f"Responding to job {job_id} with memo {memo_id} and accept {accept} and reason {reason}")
            self.contract_manager.create_memo(
                self.agent_address,
                job_id,
                f"{reason if reason else f'Job {job_id} accepted.'}",
                MemoType.MESSAGE,
                is_secured=False,
                next_phase=ACPJobPhase.TRANSACTION
            )
            print(f"Responded to job {job_id} with memo {memo_id} and accept {accept} and reason {reason}")
            return tx_hash
        except Exception as e:
            print(f"Error in respond_to_job_memo: {e}")
            print(traceback.format_exc())
            raise
    def pay_for_job(self, job_id: int, memo_id: int, amount_in_eth: Union[float, str], reason: Optional[str] = "") -> Tuple[str, str]:
        amount_in_wei = self.w3.to_wei(amount_in_eth, "ether")
        
        time.sleep(10)
        approve_tx_hash = self.contract_manager.approve_allowance(self.agent_address, amount_in_wei)
        time.sleep(10)

        set_budget_tx_hash = self.contract_manager.set_budget(self.agent_address, job_id, amount_in_wei)
        time.sleep(10)

        sign_memo_tx_hash = self.contract_manager.sign_memo(self.agent_address, memo_id, True, reason or "")
        time.sleep(10)

        create_memo_tx_hash = self.contract_manager.create_memo(
            self.agent_address,
            job_id,
            f"Job {job_id} paid. {reason if reason else ''}",
            MemoType.MESSAGE,
            is_secured=False,
            next_phase=ACPJobPhase.EVALUATION
        )
        
        print(f"Paid for job {job_id} with memo {memo_id} and amount {amount_in_eth} and reason {reason}")
        return approve_tx_hash, set_budget_tx_hash, sign_memo_tx_hash, create_memo_tx_hash

    def submit_job_deliverable(self, job_id: int, deliverable_content: str) -> str:
        tx_hash = self.contract_manager.create_memo(
            self.agent_address,
            job_id,
            deliverable_content,
            MemoType.OBJECT_URL,
            is_secured=True,
            next_phase=ACPJobPhase.COMPLETED
        )
        # print(f"Deliverable submission tx: {tx_hash} for job {job_id}")
        return tx_hash

    def evaluate_job_delivery(self, memo_id_of_deliverable: int, accept: bool, reason: Optional[str] = "") -> str:
        tx_hash = self.contract_manager.sign_memo(self.agent_address, memo_id_of_deliverable, accept, reason or "")
        print(f"Evaluation (signMemo) tx: {tx_hash} for deliverable memo ID {memo_id_of_deliverable} is {accept}")
        return tx_hash

    def get_job_details(self, job_id: int) -> IACPJob:
        return self.contract_manager.get_job_details(job_id)

    def get_active_jobs(self, page: int = 1, pageSize: int = 10) -> List["AcpJob"]:
        url = f"{self.acp_api_url}/jobs/active?pagination[page]={page}&pagination[pageSize]={pageSize}"
        headers = {
            "wallet-address": self.agent_address
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            for job in data.get("data", []):
                print(job)
                
                jobs.append(AcpJob(
                    acp_client=self,
                    id=job["onChainJobId"],
                    provider_address=job["sellerAddress"],
                    memos=[],
                    phase=ACPJobPhase(1)
                ))
            return jobs 
        except Exception as e:
            raise ACPApiError(f"Failed to get active jobs: {e}")
        
    def get_completed_jobs(self, page: int = 1, pageSize: int = 10) -> List[IACPJob]:
        url = f"{self.acp_api_url}/jobs/completed?pagination[page]=${page}&pagination[pageSize]=${pageSize}"
        headers = {
            "wallet-address": self.agent_address
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            raise ACPApiError(f"Failed to get completed jobs: {e}")
        
    def get_cancelled_jobs(self, page: int = 1, pageSize: int = 10) -> List[IACPJob]:
        url = f"{self.acp_api_url}/jobs/cancelled?pagination[page]=${page}&pagination[pageSize]=${pageSize}"
        headers = {
            "wallet-address": self.agent_address
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            raise ACPApiError(f"Failed to get cancelled jobs: {e}")
        
    def get_job_by_onchain_id(self, onchain_job_id: int) -> IACPJob:
        url = f"{self.acp_api_url}/jobs/{onchain_job_id}"
        headers = {
            "wallet-address": self.agent_address
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get("error"):
                raise ACPApiError(data["error"]["message"])
                
            return data
        except Exception as e:
            raise ACPApiError(f"Failed to get job by onchain ID: {e}")
        
    def get_memo_by_id(self, onchain_job_id: int, memo_id: int) -> Dict[str, Any]:
        url = f"{self.acp_api_url}/jobs/{onchain_job_id}/memos/{memo_id}"
        headers = {
            "wallet-address": self.agent_address
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get("error"):
                raise ACPApiError(data["error"]["message"])
                
            return data
        except Exception as e:
            raise ACPApiError(f"Failed to get memo by ID: {e}")

class AcpJobOffering:
    def __init__(
        self,
        acp_client: VirtualsACP,
        provider_address: str,
        type: str,
        price: float,
        requirementSchema: str | Dict[str, Any]
    ):
        self.acp_client = acp_client
        self.provider_address = provider_address
        self.type = type
        self.price = price
        try:
            self.requirementSchema = json.loads(json.dumps(requirementSchema))
        except json.JSONDecodeError:
            self.requirementSchema = None
            
    def initiate_job(
        self,
        price: float,
        service_requirement: Union[Dict[str, Any], str],
        expired_at: datetime
    ) -> int:
        if self.requirementSchema:
            try:
                # If service_requirement is a string, parse it as JSON
                if isinstance(service_requirement, str):
                    service_requirement = json.loads(service_requirement)
                
                validate(instance=service_requirement, schema=self.requirementSchema)
            except ValidationError as e:
                raise ValueError(f"Invalid service requirement: {str(e)}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in service requirement: {str(e)}")
            
        return self.acp_client.initiate_job(
            price,
            self.provider_address,
            service_requirement,
            expired_at
        )