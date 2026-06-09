"""
test_raw_intent_llm.py

Calls the intent LLM directly and shows:
1. The exact prompt sent to the LLM
2. The raw LLM response (before any normalization)
3. The normalized result (after processing)

Run multiple test inputs to see how the LLM behaves.
"""

import sys
import json

sys.path.insert(0, r"c:\Users\Jesintha\Documents\Internal - Copy")

import ollama

from app.prompts.intent_prompt import SYSTEM_PROMPT, build_intent_prompt
from app.services.intent_service import (
    _normalize_workflow_payload,
    IntentWorkflow,
    parse_intent,
)
from config.settings import INTENT_MODEL, OLLAMA_BASE_URL


def raw_llm_call(task_description: str):
    """Call the LLM directly and return the raw string response."""

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

    return response["message"]["content"], user_prompt


def test_intent(task_description: str):
    """Run a single intent test showing all stages."""

    print(f"\n{'='*70}")
    print(f"  INPUT: {task_description!r}")
    print(f"{'='*70}")

    # --- Stage 1: Raw LLM output ---
    try:
        raw_response, prompt_sent = raw_llm_call(task_description)
    except Exception as e:
        print(f"\n  ERROR calling LLM: {e}")
        return

    print(f"\n  [1] RAW LLM RESPONSE (exact string):")
    print(f"  {'─'*60}")
    print(f"  {raw_response}")
    print(f"  {'─'*60}")

    # --- Stage 2: Parse as JSON ---
    try:
        raw_data = json.loads(raw_response)
        print(f"\n  [2] PARSED JSON:")
        print(f"  {json.dumps(raw_data, indent=4)}")
    except json.JSONDecodeError as e:
        print(f"\n  [2] JSON PARSE ERROR: {e}")
        return

    # --- Stage 3: After normalization ---
    normalized = _normalize_workflow_payload(raw_data)
    print(f"\n  [3] AFTER NORMALIZATION:")
    print(f"  {json.dumps(normalized, indent=4)}")

    # --- Stage 4: Full parse_intent result ---
    print(f"\n  [4] FULL parse_intent() RESULT:")
    result = parse_intent(task_description)
    print(f"  {json.dumps(result, indent=4)}")

    print()


if __name__ == "__main__":

    print("\n" + "#"*70)
    print("#  INTENT SERVICE — RAW LLM OUTPUT TEST")
    print(f"#  Model: {INTENT_MODEL}")
    print(f"#  Ollama: {OLLAMA_BASE_URL}")
    print("#"*70)

    # Test cases — same input run multiple times to check consistency
    test_cases = [
        "create vlan 100 named SALES",
        "create vlan 100 named SALES",       # same input again — check consistency
        "assign interface gi1/0/1 to vlan 200",
        "delete vlan 50",
        "configure trunk on gi1/0/24 allowing vlans 10,20,30",
        "shutdown interface gi1/0/5",
    ]

    for task in test_cases:
        test_intent(task)

    # --- Also show the prompt that gets sent ---
    print(f"\n\n{'='*70}")
    print(f"  FULL PROMPT SENT TO LLM (for reference)")
    print(f"{'='*70}\n")
    sample_prompt = build_intent_prompt("create vlan 100 named SALES")
    print(sample_prompt)
