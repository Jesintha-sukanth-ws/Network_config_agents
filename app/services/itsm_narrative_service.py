from __future__ import annotations

import logging
import enum
import re
from typing import Dict, Any, Optional

from config.settings import (
    MAX_CONTEXT_CHARS,
    SERVICENOW_FIELDS_MODEL,
)
from app.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

class NarrativeType(enum.Enum):
    TASK_FAILURE = "TASK_FAILURE"
    TASK_SUCCESS = "TASK_SUCCESS"
    CR_CREATED = "CR_CREATED"
    CR_AWAITING_APPROVAL = "CR_AWAITING_APPROVAL"
    CR_IMPLEMENTING = "CR_IMPLEMENTING"
    CR_VERIFYING = "CR_VERIFYING"
    CR_SUCCESS = "CR_SUCCESS"
    CR_IDEMPOTENT_SUCCESS = "CR_IDEMPOTENT_SUCCESS"
    CR_PARTIAL_FAILURE = "CR_PARTIAL_FAILURE"
    CR_FAILURE = "CR_FAILURE"

_FALLBACK_TEMPLATES = {
    NarrativeType.TASK_FAILURE: "Automated validation could not safely complete the requested activity. No Change Request was created and no configuration changes were applied.",
    NarrativeType.TASK_SUCCESS: "Task processed successfully and lifecycle workflow initiated.",
    NarrativeType.CR_CREATED: "Automated planning and validation completed successfully. The change has been created and is awaiting approval.",
    NarrativeType.CR_AWAITING_APPROVAL: "The change request is currently in the Authorize phase and is awaiting mandatory manual approvals.",
    NarrativeType.CR_IMPLEMENTING: "The change request has been scheduled and is moving to the Implementation phase.",
    NarrativeType.CR_VERIFYING: "Implementation complete. The system is now performing post-change automated verification.",
    NarrativeType.CR_SUCCESS: "The approved change was implemented successfully and post-change validation confirmed the desired state.",
    NarrativeType.CR_IDEMPOTENT_SUCCESS: "The requested configuration state was already present on the target environment. No additional changes were required.",
    NarrativeType.CR_PARTIAL_FAILURE: "The change was processed, but some steps did not complete as expected. Please review the execution logs for details.",
    NarrativeType.CR_FAILURE: "The approved change could not be completed successfully and requires manual review.",
}

class ITSMNarrativeService:
    def __init__(self):
        self.model = SERVICENOW_FIELDS_MODEL
        self.client = OllamaClient()

    def _sanitize(self, data: Any) -> str:
        """Removes potential secrets using regex and limits text size."""
        str_data = str(data)
        
        # Regex-based redaction for sensitive patterns
        sensitive_patterns = [
            r"password", r"secret", r"token", r"credential", r"username",
            r"bearer", r"api_key", r"auth_token", r"community", r"private_key", r"secret_key"
        ]
        pattern = re.compile(rf"(?i)({'|'.join(sensitive_patterns)})[\s:=]+[^\s]+", re.IGNORECASE)
        str_data = pattern.sub(r"\1=REDACTED", str_data)
            
        # Truncate to max context
        if len(str_data) > MAX_CONTEXT_CHARS:
            str_data = str_data[:MAX_CONTEXT_CHARS] + "... [TRUNCATED]"
            
        return str_data

    def _clean_output(self, content: str) -> str:
        """Removes markdown, code fences, and cleans up the generated text."""
        # Remove code fences
        content = re.sub(r"```[a-zA-Z]*", "", content)
        # Remove markdown headers
        content = re.sub(r"^#+\s.*", "", content, flags=re.MULTILINE)
        return content.strip()

    def _generate_narrative(self, narrative_type: NarrativeType, prompt_content: str) -> str:
        """Internal helper to call Ollama via project client and handle fallbacks."""
        try:
            system_prompt = (
                "You are an expert ITSM Change Coordinator. Your task is to generate professional, "
                "human-readable narratives for IT work notes. "
                "Output MUST be concise, auditor-friendly, and strictly no longer than 200 words. "
                "DO NOT use markdown, code blocks, technical jargon (unless necessary), CLI commands, "
                "or configuration snippets. Explain the outcome, impact, and any necessary "
                "next steps clearly."
            )

            # Use the dedicated generate() contract
            content = self.client.generate(
                prompt=prompt_content,
                system=system_prompt
            )
            
            if not content:
                raise ValueError("Empty response from LLM")

            # Clean output
            cleaned_content = self._clean_output(content)
            
            # Enforce deterministic word limit
            words = cleaned_content.split()
            if len(words) > 200:
                cleaned_content = " ".join(words[:200])
            
            logger.info("Successfully generated narrative for type: %s", narrative_type.value)
            return cleaned_content

        except Exception as e:
            logger.error("Failed to generate narrative for %s, using fallback: %s", narrative_type.value, e)
            return _FALLBACK_TEMPLATES.get(narrative_type, "Action completed.")

    def generate_task_work_notes(
        self,
        narrative_type: NarrativeType,
        task_number: str,
        short_description: str,
        description: str,
        technical_details: Any
    ) -> str:
        """Generates work notes for SCTASKs."""
        sanitized_details = self._sanitize(technical_details)
        prompt = (
            f"Generate an ITSM work note for Task {task_number}: {short_description}. "
            f"Context: {description}. "
            f"Outcome/Technical Details: {sanitized_details}. "
            f"State: {narrative_type.value}."
        )
        return self._generate_narrative(narrative_type, prompt)

    def generate_cr_work_note(
        self,
        narrative_type: NarrativeType,
        change_number: str,
        short_description: str,
        technical_details: Any
    ) -> str:
        """Generates work notes for Change Requests."""
        sanitized_details = self._sanitize(technical_details)
        prompt = (
            f"Generate an ITSM work note for Change Request {change_number}: {short_description}. "
            f"Outcome/Technical Details: {sanitized_details}. "
            f"State: {narrative_type.value}."
        )
        return self._generate_narrative(narrative_type, prompt)

    def generate_cr_close_notes(
        self,
        narrative_type: NarrativeType,
        change_number: str,
        short_description: str,
        execution_summary: Any
    ) -> str:
        """Generates close notes for Change Requests."""
        sanitized_summary = self._sanitize(execution_summary)
        prompt = (
            f"Generate professional CR close notes for {change_number}: {short_description}. "
            f"Execution Summary: {sanitized_summary}. "
            f"Outcome: {narrative_type.value}."
        )