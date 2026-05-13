from pydantic import BaseModel
from typing import List, Dict, Any


class WorkflowStep(BaseModel):
    intent_type: str
    parameters: Dict[str, Any]


class IntentWorkflow(BaseModel):
    workflow: List[WorkflowStep]