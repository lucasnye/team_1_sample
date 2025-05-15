# virtuals_acp/contract_manager.py

import json
import time
from datetime import datetime
import traceback
from typing import Optional, Tuple

from eth_account import Account
import requests
from web3 import Web3
import web3
from web3.contract import Contract
from eth_account.signers.local import LocalAccount

from .abi import ACP_ABI, ERC20_ABI
from .configs import ACPContractConfig
from .models import ACPJobPhase, MemoType, ACPJob, IMemo # ACPMemo might be useful here too
from .exceptions import ACPContractError, TransactionFailedError
from eth_account.messages import encode_defunct


class _ACPContractManager:
    def __init__(self, web3_client: Web3, config: ACPContractConfig, wallet_private_key: str):
        self.w3 = web3_client
        self.account = Account.from_key(wallet_private_key)
        self.config = config
        
     
        self.contract: Contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.contract_address), abi=ACP_ABI
        )
        self.token_contract: Contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.virtuals_token_address), abi=ERC20_ABI
        )
        
    def validate_transaction(self, hash_value: str) -> object:
        try:
            response = requests.post(f"{self.config.acp_api_url}/acp-agent-wallets/trx-result", json={"userOpHash": hash_value})
            return response.json()
        except Exception as error:
            print(traceback.format_exc())
            raise Exception(f"Failed to get job_id {error}")
    
    def _sign_transaction(self, method_name: str, args: list, contract_address: Optional[str] = None) -> Tuple[dict, str]:
        if contract_address:
            encoded_data = self.token_contract.encode_abi(method_name, args=args)
        else:
            encoded_data = self.contract.encode_abi(method_name, args=args)
        
        trx_data = {
            "target": contract_address if contract_address else self.config.contract_address,
            "value": "0",
            "data": encoded_data
        }
        
        message_json = json.dumps(trx_data, separators=(",", ":"), sort_keys=False)
        message_bytes = message_json.encode()
        
        # Sign the transaction
        message = encode_defunct(message_bytes)
        signature =  self.account.sign_message(message).signature.hex()
        return trx_data, signature

    def create_job(
        self,
        agent_wallet_address: str,
        provider_address: str,
        evaluator_address: str,
        expire_at: datetime
    ) -> dict:
        try:
            provider_address = Web3.to_checksum_address(provider_address)
            evaluator_address = Web3.to_checksum_address(evaluator_address)
            expire_timestamp = int(expire_at.timestamp())
        
            # Sign the transaction
            trx_data, signature = self._sign_transaction(
                "createJob", 
                [provider_address, evaluator_address, expire_timestamp]
            )
                
            # Prepare payload
            payload = {
                "agentWallet": agent_wallet_address,
                "trxData": trx_data,
                "signature": signature
            }
            # Submit to custom API
            api_url = f"{self.config.acp_api_url}/acp-agent-wallets/transactions"
            response = requests.post(api_url, json=payload)
            
            if response.json().get("error"):
                raise Exception(f"Failed to create job {response.json().get('error').get('status')}, Message: {response.json().get('error').get('message')}")
            
            # Return transaction hash or response ID
            return {"txHash": response.json().get("data", {}).get("userOpHash", "")}
        except Exception as e:
            raise

    def approve_allowance(self, agent_wallet_address: str, price_in_wei: int) -> str:
        try:
            trx_data, signature = self._sign_transaction(
                "approve", 
                [self.config.contract_address, price_in_wei],
                self.config.virtuals_token_address
            )
            
            payload = {
                "agentWallet": agent_wallet_address,
                "trxData": trx_data,
                "signature": signature
            }
            
            api_url = f"{self.config.acp_api_url}/acp-agent-wallets/transactions"
            response = requests.post(api_url, json=payload)
            
            if (response.json().get("error")):
                raise Exception(f"Failed to approve allowance {response.json().get('error').get('status')}, Message: {response.json().get('error').get('message')}")
            
            return response.json()
        except Exception as e:
            print(f"An error occurred while approving allowance: {e}")
            raise
        
    def create_memo(self, agent_wallet_address: str, job_id: int, content: str, memo_type: MemoType, is_secured: bool, next_phase: ACPJobPhase) -> str:
        retries = 3
        error = None

        while retries > 0:
            try:
                trx_data, signature = self._sign_transaction(
                    "createMemo", 
                    [job_id, content, memo_type.value, is_secured, next_phase.value]
                )
                

                payload = {
                    "agentWallet": agent_wallet_address,
                    "trxData": trx_data,
                    "signature": signature
                }
                

                api_url = f"{self.config.acp_api_url}/acp-agent-wallets/transactions"
                response = requests.post(api_url, json=payload)
                
                if (response.json().get("error")):
                    raise Exception(f"Failed to create memo {response.json().get('error').get('status')}, Message: {response.json().get('error').get('message')}")
                
                return { "txHash": response.json().get("txHash", response.json().get("id", "")), "memoId": response.json().get("memoId", "")}
            except Exception as e:
                print(f"{e}")
                print(traceback.format_exc())
                error = e
                retries -= 1
                time.sleep(2 * (3 - retries))
                
            if error:
                raise Exception(f"{error}")


    def sign_memo(
        self,
        agent_wallet_address: str,
        memo_id: int,
        is_approved: bool,
        reason: Optional[str] = ""
    ) -> str:
        retries = 3
        error = None
        while retries > 0:
            try:
                trx_data, signature = self._sign_transaction(
                    "signMemo", 
                    [memo_id, is_approved, reason]
                )
                
                payload = {
                    "agentWallet": agent_wallet_address,
                    "trxData": trx_data,
                    "signature": signature
                }
                
                api_url = f"{self.config.acp_api_url}/acp-agent-wallets/transactions"
                response = requests.post(api_url, json=payload)
                
                if (response.json().get("error")):
                    raise Exception(f"Failed to sign memo {response.json().get('error').get('status')}, Message: {response.json().get('error').get('message')}")
                
                return response.json()
                
            except Exception as e:
                error = e
                print(f"{error}")
                print(traceback.format_exc())
                retries -= 1
                time.sleep(2 * (3 - retries))
                
        raise Exception(f"Failed to sign memo {error}")
    
    def set_budget(self, agent_wallet_address: str, job_id: int, budget: int) -> str:
        try:
            trx_data, signature = self._sign_transaction(
                "setBudget", 
                [job_id, budget]
            )
            
            payload = {
                "agentWallet": agent_wallet_address,
                "trxData": trx_data,
                "signature": signature
            }
            
            api_url = f"{self.config.acp_api_url}/acp-agent-wallets/transactions"
            response = requests.post(api_url, json=payload)
            
            if (response.json().get("error")):
                raise Exception(f"Failed to set budget {response.json().get('error').get('status')}, Message: {response.json().get('error').get('message')}")
            
            return response.json()
        except Exception as error:
            raise Exception(f"{error}")

    def get_job_details(self, job_id: int) -> ACPJob:
        try:
            # Call structure: (id, client, provider, budget, amountClaimed, phase, memoCount, expiredAt, evaluator)
            job_data_tuple = self.contract.functions.jobs(job_id).call()
            
            return ACPJob(
                id=job_data_tuple[0],
                client_address=job_data_tuple[1],
                provider_address=job_data_tuple[2],
                budget=job_data_tuple[3],
                amount_claimed=job_data_tuple[4],
                phase=ACPJobPhase(job_data_tuple[5]),
                memo_count=job_data_tuple[6],
                expired_at_timestamp=job_data_tuple[7],
                evaluator_address=job_data_tuple[8],
                memos=[] # Memos need to be fetched separately using client.get_job_memos
            )
        except Exception as e:
            raise ACPContractError(f"Failed to get job details for job {job_id}: {e}")
        
    def get_memo_by_job(
        self,
        job_id: int,
        memo_type: Optional[MemoType] = None
    ) -> Optional[IMemo]:
        try:
            memos = self.contract.functions.getAllMemos(job_id).call()
            
            if memo_type is not None:
                filtered_memos = [m for m in memos if m['memoType'] == memo_type]
                return filtered_memos[-1] if filtered_memos else None
            else:
                return memos[-1] if memos else None
        except Exception as error:
            raise Exception(f"Failed to get memo by job {error}")
        
    def get_memos_for_phase(
        self,
        job_id: int,
        phase: int,
        target_phase: int
    ) -> Optional[IMemo]:
        try:
            memos = self.contract.functions.getMemosForPhase(job_id, phase).call()
            
            target_memos = [m for m in memos if m['nextPhase'] == target_phase]
            return target_memos[-1] if target_memos else None
        except Exception as error:
            raise Exception(f"Failed to get memos for phase {error}")