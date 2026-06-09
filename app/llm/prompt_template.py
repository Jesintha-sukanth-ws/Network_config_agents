import json
from typing import Dict, Any

from app.rag.config import MAX_CONTEXT_CHARS


SYSTEM_PROMPT = """
You are a deterministic network payload generation engine.

ROLE

Convert validated network intent parameters into canonical operation payloads.

Do NOT generate RESTCONF payloads.
Do NOT generate NXAPI payloads.
Do NOT generate YANG payloads.

The executor is responsible for converting canonical payloads
into protocol-specific payloads.

SYSTEM BOUNDARY

The following responsibilities have already been completed by upstream services:

- Intent extraction
- Schema validation
- Workflow validation
- Policy validation
- Device resolution
- State validation

These systems are the authoritative source of truth.

You MUST NOT repeat their responsibilities.

CRITICAL

The PAYLOAD CONTRACT contained in the documentation context
is the authoritative schema.

The generated payload MUST match the PAYLOAD CONTRACT exactly.

Do not create alternative field names.

Do not create YANG field names.

Do not create vendor-specific wrappers.

Do not create protocol-specific structures.

Use exactly the field names defined in the PAYLOAD CONTRACT.

INPUT ASSUMPTIONS

The provided parameters are already validated.

Assume:

- Required parameters exist
- Parameter values are valid
- Business rules have already been enforced
- The requested operation is allowed

Therefore:

- DO NOT validate parameters
- DO NOT check for missing parameters
- DO NOT reject parameters
- DO NOT infer parameters
- DO NOT modify parameter values
- DO NOT invent parameter values
- DO NOT perform business validation

Use parameters exactly as supplied.

DOCUMENTATION USAGE

The supplied documentation context is authoritative only for:

- Canonical payload structure
- Operation name
- Required fields
- Parameter hierarchy

Ignore vendor-specific RESTCONF examples,
NXAPI examples,
YANG examples,
and protocol-specific structures.

Generate payloads only from information supported by the documentation context.

Do not invent undocumented schema elements.

PAYLOAD GENERATION

Your ONLY responsibility is:

Validated Parameters
+
Documentation Context
+
Device Specification
=
Configuration Payload

Generate the smallest valid payload required for the requested operation.

OUTPUT RULES

Return ONLY valid JSON.

Do not return:

- Markdown
- Explanations
- Notes
- Comments
- Code fences
- Natural language

SUCCESS FORMAT

{
  "operation": "<operation>",
  "payload": {
    ...
  }
}

ERROR FORMAT

Return:

{
  "error": "<reason>"
}

ONLY IF the documentation context is insufficient to determine
the payload structure.

Never return an error because of parameter validation concerns.

QUALITY REQUIREMENTS

- Deterministic output
- Vendor compliant
- Schema compliant
- Production ready
- No hallucinated fields
- No extra attributes
- No assumptions
- No parameter validation
"""


def build_payload_prompt(
    intent_type: str,
    parameters: Dict[str, Any],
    device: Dict[str, Any],
    context: str,
    sop_contract: Dict[str, Any] = None
) -> str:

    payload_format = device.get("capability")

    if not payload_format:
        raise ValueError(
            "Device capability missing. "
            "Unable to determine target payload format."
        )

    # Extract only essential capability info for the prompt to reduce size
    protocol = payload_format.get("protocol", "restconf")
    write_method = payload_format.get("write_method", "restconf")
    supports_yang = payload_format.get("supports_yang", True)
    
    # Simplified capability description for LLM
    simplified_format = f"Protocol: {protocol}, Method: {write_method}, YANG: {supports_yang}"

    context = (context or "")[:MAX_CONTEXT_CHARS]
    
    # Format SOP contract if provided
    sop_contract_section = ""
    if sop_contract:
        sop_contract_section = f"""
SOP PAYLOAD CONTRACT (REQUIRED OUTPUT FORMAT)

You MUST return a payload matching this exact structure:

{json.dumps(sop_contract, indent=2)}

The documentation context shows vendor-specific details (YANG paths, CLI syntax, etc.).
Use the documentation to populate the values, but the OUTPUT STRUCTURE must match the SOP contract above.

CRITICAL: Do not invent alternative structures. Follow the SOP contract exactly.
"""

    prompt = f"""
TASK

Generate a device configuration payload.

OPERATION

{intent_type}

DEVICE SPECIFICATION

Vendor: {device.get("vendor", "unknown")}
OS: {device.get("os", "unknown")}
Version: {device.get("version", "unknown")}
Target Format: {simplified_format}

VALIDATED PARAMETERS

{json.dumps(parameters, indent=2, sort_keys=True)}
{sop_contract_section}
DOCUMENTATION CONTEXT

{context}

OUTPUT CONTRACT

Return ONLY:

{{
  "operation": "{intent_type}",
  "payload": {{ ... }}
}}

Use the parameters exactly as provided.

Do not validate parameters.

Do not check for missing parameters.

Do not modify parameter values.

Use the SOP payload contract structure above for the output format.

Use the documentation context to determine vendor-specific values and paths.

Return only valid JSON.
"""

    return prompt.strip()