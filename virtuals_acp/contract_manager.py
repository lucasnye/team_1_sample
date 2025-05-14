# virtuals_acp/contract_manager.py

import time
from datetime import datetime
from typing import Optional, Tuple

from web3 import Web3
import web3
from web3.contract import Contract
from eth_account.signers.local import LocalAccount

from .abi import ACP_ABI, ERC20_ABI
from .configs import ACPContractConfig
from .models import ACPJobPhase, MemoType, ACPJob # ACPMemo might be useful here too
from .exceptions import ACPContractError, TransactionFailedError

class _ACPContractManager:
    def __init__(self, web3_client: Web3, account: LocalAccount, config: ACPContractConfig):
        self.w3 = web3_client
        self.account = account # This is the signer_account
        self.config = config
        self.contract: Contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.contract_address), abi=ACP_ABI
        )
        self.token_contract: Contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.virtuals_token_address), abi=ERC20_ABI
        )

    def _get_nonce(self) -> int:
        return self.w3.eth.get_transaction_count(self.account.address)

    def _send_transaction(self, func_call, gas_limit: int = 2000000) -> str: # Added gas_limit
        try:
            estimated_gas = func_call.estimate_gas({'from': self.account.address})
            # Add a buffer to estimated gas
            gas_to_use = int(estimated_gas * 1.2) if estimated_gas else gas_limit
        except Exception as e:
            # print(f"Could not estimate gas, using default {gas_limit}. Error: {e}")
            gas_to_use = gas_limit


        try:
            # For EIP-1559 chains (like Base):
            if self.config.chain_id == 8453 or self.config.chain_id == 84532 : # Base mainnet or Sepolia
                max_fee_per_gas = self.w3.eth.max_priority_fee + self.w3.eth.get_block('latest')['baseFeePerGas'] * 2
                max_priority_fee_per_gas = self.w3.eth.max_priority_fee
                tx_params = {
                    'chainId': self.config.chain_id,
                    'gas': gas_to_use,
                    'maxFeePerGas': max_fee_per_gas,
                    'maxPriorityFeePerGas': max_priority_fee_per_gas,
                    'nonce': self._get_nonce(),
                    'from': self.account.address
                }
            else: # For legacy chains
                 tx_params = {
                    'chainId': self.config.chain_id,
                    'gas': gas_to_use,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self._get_nonce(),
                    'from': self.account.address
                }

            tx = func_call.build_transaction(tx_params)
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # print(f"Transaction sent: {tx_hash.hex()}. Waiting for receipt...")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180) # 3 mins timeout
            
            if receipt.status == 0:
                # print(f"Transaction {tx_hash.hex()} failed. Receipt: {receipt}")
                raise TransactionFailedError(f"Transaction {tx_hash.hex()} failed.") # Receipt can be large
            # print(f"Transaction {tx_hash.hex()} successful.")
            return tx_hash.hex()
        except TransactionFailedError:
            raise # Re-raise specific error
        except Exception as e:
            # print(f"Error sending transaction: {e}")
            raise ACPContractError(f"Error sending transaction: {e}")


    def _get_job_id_from_receipt(self, tx_hash: str) -> Optional[int]:
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if not receipt:
                # print(f"No receipt found for tx {tx_hash}")
                return None
            
            logs = self.contract.events.JobCreated().process_receipt(receipt, errors=web3.logs.DISCARD) # Use DISCARD for non-matching logs
            if logs:
                return logs[0]['args']['jobId']
            # print(f"JobCreated event not found in receipt for tx {tx_hash}")
            return None
        except Exception as e:
            # print(f"Error processing receipt for job ID: {e}")
            return None


    def create_job(self, provider_address: str, evaluator_address: str, expire_at: datetime) -> Tuple[str, int]:
        expire_at_timestamp = int(expire_at.timestamp())
        func = self.contract.functions.createJob(
            Web3.to_checksum_address(provider_address),
            Web3.to_checksum_address(evaluator_address),
            expire_at_timestamp
        )
        tx_hash = self._send_transaction(func)
        
        # Robust Job ID retrieval
        job_id = None
        # Retry mechanism for event propagation, if necessary
        for _ in range(5): # Try for ~10-15 seconds
            job_id = self._get_job_id_from_receipt(tx_hash)
            if job_id is not None:
                break
            time.sleep(3)
            
        if job_id is None:
            raise ACPContractError(f"Failed to retrieve JobID from tx receipt {tx_hash} after multiple attempts.")

        return tx_hash, job_id

    def approve_allowance(self, amount_in_wei: int) -> str:
        func = self.token_contract.functions.approve(
            Web3.to_checksum_address(self.config.contract_address),
            amount_in_wei
        )
        return self._send_transaction(func, gas_limit=100000) # Approvals are usually cheaper

    def create_memo(self, job_id: int, content: str, memo_type: MemoType, is_secured: bool, next_phase: ACPJobPhase) -> str:
        retries = 3
        last_error = None
        for attempt in range(retries):
            try:
                func = self.contract.functions.createMemo(
                    job_id, content, memo_type.value, is_secured, next_phase.value
                )
                # print(f"Attempting to create memo for job {job_id}: content='{content[:30]}...', type={memo_type.name}, next_phase={next_phase.name}")
                return self._send_transaction(func)
            except Exception as e:
                # print(f"Attempt {attempt+1} to create memo failed: {e}")
                last_error = e
                time.sleep(2 * (attempt + 1)) 
        raise ACPContractError(f"Failed to create memo for job {job_id} after {retries} retries: {last_error}")


    def sign_memo(self, memo_id: int, is_approved: bool, reason: Optional[str] = "") -> str:
        retries = 3
        last_error = None
        for attempt in range(retries):
            try:
                func = self.contract.functions.signMemo(memo_id, is_approved, reason or "")
                # print(f"Attempting to sign memo {memo_id}: approved={is_approved}, reason='{reason[:30]}...'")
                return self._send_transaction(func)
            except Exception as e:
                # print(f"Attempt {attempt+1} to sign memo {memo_id} failed: {e}")
                last_error = e
                time.sleep(2 * (attempt + 1))
        raise ACPContractError(f"Failed to sign memo {memo_id} after {retries} retries: {last_error}")

    def set_budget(self, job_id: int, budget_in_wei: int) -> str:
        func = self.contract.functions.setBudget(job_id, budget_in_wei)
        # print(f"Attempting to set budget for job {job_id} to {budget_in_wei} wei")
        return self._send_transaction(func)

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