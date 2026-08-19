from pydantic import BaseModel
from typing import Optional

class InfisicalProject(BaseModel):
    secretPath: str = "/"

class InfisicalWebhookPayload(BaseModel):
    project: Optional[InfisicalProject] = None

class InfisicalWebhookResponse(BaseModel):
    gcp_restarted_queued: bool 
    status: str = "success"
    queued: bool = True