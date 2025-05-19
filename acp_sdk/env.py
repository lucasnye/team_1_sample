from pydantic_settings import BaseSettings
from pydantic import field_validator

class EnvSettings(BaseSettings):
    WHITELISTED_WALLET_PRIVATE_KEY: str
    WHITELISTED_WALLET_ENTITY_ID: int
    BUYER_WALLET_ADDRESS: str
    SELLER_WALLET_ADDRESS: str
    EVALUATOR_WALLET_ADDRESS: str

    @field_validator("WHITELISTED_WALLET_PRIVATE_KEY")
    @classmethod
    def strip_0x_prefix(cls, v: str) -> str:
        print(f"Validating WHITELISTED_WALLET_PRIVATE_KEY: {v}")
        if v.startswith("0x"):
            raise ValueError("WHITELISTED_WALLET_PRIVATE_KEY must not start with '0x'. Please remove it.")
        return v

    @field_validator("BUYER_WALLET_ADDRESS", "SELLER_WALLET_ADDRESS", "EVALUATOR_WALLET_ADDRESS")
    @classmethod
    def validate_wallet_address(cls, v: str) -> str:
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Wallet address must start with '0x' and be 42 characters long.")
        return v
    