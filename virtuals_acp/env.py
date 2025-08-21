from typing import Optional
from pydantic_settings import BaseSettings
from strings import hexdigits
from pydantic import field_validator

class EnvSettings(BaseSettings):
    WHITELISTED_WALLET_PRIVATE_KEY: Optional[str] = "99d3bb451fe7e947d843cafb0cb735f01f1cd5905b174406b82550acfdc8ffa6"
    BUYER_AGENT_WALLET_ADDRESS: Optional[str] = "0xE528FD304780d5c3C06f4e894D91bfD28C71a1f8"
    SELLER_AGENT_WALLET_ADDRESS: Optional[str] = "0x3DDfA8C8EFEf8f6C257B827d7c9e9cE893ADe8D1"
    EVALUATOR_AGENT_WALLET_ADDRESS: Optional[str] = None
    BUYER_GAME_TWITTER_ACCESS_TOKEN: Optional[str] = None
    SELLER_GAME_TWITTER_ACCESS_TOKEN: Optional[str] = None
    EVALUATOR_GAME_TWITTER_ACCESS_TOKEN: Optional[str] = None
    BUYER_ENTITY_ID: Optional[int] = 2
    SELLER_ENTITY_ID: Optional[int] = 1
    EVALUATOR_ENTITY_ID: Optional[int] = None

    @field_validator("BUYER_AGENT_WALLET_ADDRESS", "SELLER_AGENT_WALLET_ADDRESS", "EVALUATOR_AGENT_WALLET_ADDRESS")
    def validate_wallet_address(cls, v: str) -> str:
        if v is None:
            return None
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Wallet address must start with '0x' and be 42 characters long.")
        return v
