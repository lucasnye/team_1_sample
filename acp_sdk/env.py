from pydantic_settings import BaseSettings
from pydantic import validator

class EnvSettings(BaseSettings):
    WHITELISTED_WALLET_PRIVATE_KEY: str
    WHITELISTED_WALLET_ENTITY_ID: int
    BUYER_WALLET_ADDRESS: str
    SELLER_WALLET_ADDRESS: str
    EVALUATOR_WALLET_ADDRESS: str

    @validator("WHITELISTED_WALLET_PRIVATE_KEY")
    def strip_0x_prefix(cls, v: str) -> str:
        return v[2:] if v.startswith("0x") else v

    @validator("BUYER_WALLET_ADDRESS", "SELLER_WALLET_ADDRESS", "EVALUATOR_WALLET_ADDRESS")
    def wallet_address_should_start_with_0x(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Wallet address must start with '0x' and be 42 characters long")
        return v
