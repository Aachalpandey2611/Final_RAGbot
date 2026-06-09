from typing import Dict
from pydantic import BaseModel, Field

class HealthCheck(BaseModel):
    status: str = Field(..., description="Application status, e.g., 'healthy'")
    environment: str = Field(..., description="Running environment, e.g., 'production', 'local'")
    services: Dict[str, str] = Field(..., description="Dictionary representing dependencies status (e.g., database: online)")
