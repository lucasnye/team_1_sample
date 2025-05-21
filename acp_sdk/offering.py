from datetime import datetime
import json
from typing import Any, Dict, Optional, Union, TYPE_CHECKING
from pydantic import BaseModel, field_validator, ConfigDict
from jsonschema import ValidationError, validate

if TYPE_CHECKING:
    from acp_sdk.client import VirtualsACP

class ACPJobOffering(BaseModel):
    acp_client: "VirtualsACP"
    provider_address: str
    type: str
    requirementSchema: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    

    @field_validator('requirementSchema', mode='before')
    def parse_requirement_schema(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(json.dumps(v))
            except json.JSONDecodeError:
                return None
        return v

    def initiate_job(
        self,
        service_requirement: Union[Dict[str, Any], str],
        expired_at: datetime,
        evaluator_address: Optional[str] = None
    ) -> int:
        if self.requirementSchema:
            try:
                service_requirement = json.loads(json.dumps(service_requirement))
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON in service requirement. Required format: {json.dumps(self.requirementSchema, indent=2)}")

            try:
                validate(instance=service_requirement, schema=self.requirementSchema)
            except ValidationError as e:
                raise ValueError(f"Invalid service requirement: {str(e)}")
            

        return self.acp_client.initiate_job(
            provider_address=self.provider_address,
            service_requirement=service_requirement,
            evaluator_address=evaluator_address,
            expired_at=expired_at,
        )