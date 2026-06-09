import json
import logging
from typing import Dict, Any, List
import ollama
from pydantic import BaseModel, ValidationError
from app.registry.intent_registry import (get_canonical_intent,CANONICAL_INTENT_SCHEMAS,)
from app.prompts.intent_prompt import (SYSTEM_PROMPT,build_intent_prompt,)
from config.settings import (INTENT_MODEL,OLLAMA_BASE_URL,OLLAMA_TIMEOUT,)

logger = logging.getLogger(__name__)


class WorkflowStep(BaseModel):
    intent_type: str
    parameters: Dict[str, Any]

class IntentWorkflow(BaseModel):
    workflow: List[WorkflowStep]

_STEP_DISCRIMINATORS = ("intent_type",)

def _looks_like_step(value: Any) -> bool:
    return isinstance(value, dict) and any(
        key in value for key in _STEP_DISCRIMINATORS
    )


def _flatten_step(step: Dict[str, Any]) -> Dict[str, Any]:

    if "intent_type" in step and isinstance(step.get("parameters"), dict):
        return step
    if "intent_type" in step:
        intent_name = step.pop("intent_type")
        parameters = step.pop("parameters", None)
        
        if not isinstance(parameters, dict):
            parameters = {}

        for key, value in list(step.items()):
            parameters.setdefault(key, value)
        return {
            "intent_type": intent_name,
            "parameters": parameters,
        }

    # # Legacy "intent" key with parameters scattered at the top level
    # if "intent" in step:
    #     intent_name = step.pop("intent")
    #     parameters = step.pop("parameters", None)
    #     if not isinstance(parameters, dict):
    #         parameters = {}
    #     for key, value in list(step.items()):
    #         parameters.setdefault(key, value)
    #     return {
    #         "intent_type": intent_name,
    #         "parameters": parameters,
    #     }

    # Unknown shape — return untouched so Pydantic produces a clear error
    return step


def _normalize_workflow_payload(raw_data: Any) -> Any:
   
    if not isinstance(raw_data, dict):
        return raw_data

    if "workflow" not in raw_data and _looks_like_step(raw_data):
        return {"workflow": [_flatten_step(dict(raw_data))]}

    workflow = raw_data.get("workflow")

    
    if isinstance(workflow, dict):
        workflow = [workflow]

    
    if not isinstance(workflow, list):
        return raw_data

    
    raw_data["workflow"] = [
_flatten_step(dict(step)) if isinstance(step, dict) else step
        for step in workflow
    ]
    return raw_data


class IntentService:

    def parse(self, task_description: str) -> Dict[str, Any]:
        return parse_intent(task_description)


def parse_intent(task_description: str) -> Dict[str, Any]:

    try:

        user_prompt = build_intent_prompt(task_description)

        client = ollama.Client(host=OLLAMA_BASE_URL)

        response = client.chat(
            model=INTENT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            format="json",
        )

        raw_response = response["message"]["content"]

       
        logger.info(
            "Raw LLM response:\n%s",
            raw_response,
        )

        raw_data = json.loads(raw_response)

       
        if isinstance(raw_data, dict) and "error" in raw_data and "workflow" not in raw_data:
            logger.warning(
                "LLM declined the request: %s",
                raw_data.get("error"),
            )
            return {"error": str(raw_data.get("error"))}

      
        normalized_response = _normalize_workflow_payload(raw_data)

        logger.info(
            "Normalized response:\n%s",
            json.dumps(normalized_response, indent=2),
        )


        workflow = IntentWorkflow(**normalized_response)

        verified_steps = []

        for step in workflow.workflow:

            canonical = get_canonical_intent(step.intent_type)

            if not canonical:

                logger.warning(
                    "Unsupported intent: %s",
                    step.intent_type,
                )

                return {
                    "error": f"Invalid intent: {step.intent_type}"
                }

            verified_steps.append({
                **step.model_dump(),
                "intent_type": canonical,
            })

        return {"workflow": verified_steps}

    except json.JSONDecodeError:

        logger.error("LLM returned invalid JSON")

        return {"error": "Invalid JSON from model"}

    except ValidationError as e:

        logger.error("Schema error: %s", e)

        return {"error": "Invalid workflow structure"}

    except Exception as e:

        logger.exception("Intent service failed")

        return {"error": f"Intent parsing unavailable: {e}"}
