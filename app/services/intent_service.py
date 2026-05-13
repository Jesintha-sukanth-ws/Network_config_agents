import json
import ollama

from app.prompts.intent_prompt import SYSTEM_PROMPT
from app.models.intent_models import IntentWorkflow
from app.policies.workflow_policy_engine import WorkflowPolicyEngine


MODEL_NAME = "gpt-oss:120b-cloud"  


def parse_intent(task_description: str):

    try:

        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": task_description
                }
            ],
            format="json"
        )

        content = response["message"]["content"]

        print("\n MODEL OUTPUT:\n")
        print(content)

        parsed_json = json.loads(content)

        validated = IntentWorkflow(**parsed_json)

        return validated.model_dump()

    except Exception as e:

        return {
            "error": str(e)
        }