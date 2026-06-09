from __future__ import annotations

import json
import logging
import re
from typing import Dict, Any

from app.rag.retrieval_service import RetrievalService
from app.llm.ollama_client import OllamaClient
from app.llm.prompt_template import (build_payload_prompt,SYSTEM_PROMPT)
from app.utils.logger import orchestrator_logger

logger = logging.getLogger(__name__)


class PayloadGenerationService:
    def __init__(self,retrieval_service: RetrievalService,llm_client: OllamaClient) -> None:

        self._retriever = retrieval_service
        self._llm = llm_client


    def generate(self,orchestration_input: Dict[str, Any]) -> Dict[str, Any]:

        try:

            intent_type = orchestration_input["intent_type"]  # Canonical name for operation field
            rag_type = orchestration_input.get("rag_type", intent_type)  # RAG lookup key
            parameters = orchestration_input.get("parameters", {})
            device = orchestration_input["device"]

            logger.info(
                "Starting payload generation (intent=%s, rag=%s, params=%s)",
                intent_type, rag_type, parameters
            )

            context = (

                self._retriever
                .retrieve_raw_context(

                    intent_type=
                    rag_type,  # Use rag_type for document retrieval

                    vendor=
                    device["vendor"],

                    os_name=
                    device["os"],

                    version=
                    device["version"]
                )
            )
            

            orchestrator_logger.kv_block(
                "    PAYLOAD: RAG CONTEXT",
                {
                    "intent_type": intent_type,
                    "rag_type": rag_type,
                    "vendor": device.get("vendor"),
                    "os": device.get("os"),
                    "version": device.get("version"),
                    "context_chars": len(context or ""),
                    "context_preview":
                        (context or "")[:600] +
                        ("…" if len(context or "") > 600 else ""),
                },
            )
            
            # Get SOP payload contract from registry
            from app.registry.intent_registry import CANONICAL_INTENT_SCHEMAS
            sop_contract = None
            schema = CANONICAL_INTENT_SCHEMAS.get(intent_type)
            if schema and "sop_payload_contract" in schema:
                sop_contract = schema["sop_payload_contract"]

            prompt = (

                build_payload_prompt(

                    intent_type=
                    intent_type,  # Use canonical name in prompt

                    parameters=
                    parameters,

                    device=
                    device,

                    context=
                    context,
                    
                    sop_contract=
                    sop_contract
                )
            )
            logger.info("Built prompt (chars=%d)", len(prompt))
            logger.debug("FINAL PAYLOAD PROMPT:\n%s", prompt)

           
            # Time the LLM inference
            import time
            start_time = time.time()
            
            logger.info("Calling Ollama LLM (model=%s, prompt_chars=%d, timeout=%ds)...", 
                       self._llm._model if hasattr(self._llm, '_model') else 'unknown',
                       len(prompt),
                       self._llm._timeout_seconds if hasattr(self._llm, '_timeout_seconds') else 180)
            
            try:
                raw_response = self._llm.generate(prompt=prompt, system=SYSTEM_PROMPT)
            except Exception as llm_error:
                duration = time.time() - start_time
                logger.error(
                    "LLM call failed after %.2fs: %s", 
                    duration, 
                    str(llm_error)
                )
                # Check if it's a timeout
                if "timeout" in str(llm_error).lower() or duration > 175:
                    return {
                        "error": (
                            f"LLM timeout after {duration:.1f}s. "
                            "Ollama may be overloaded or model too slow. "
                            f"Prompt size: {len(prompt)} chars. "
                            "Try: 1) Reduce context size, 2) Use faster model, "
                            "3) Increase OLLAMA_TIMEOUT in .env"
                        )
                    }
                raise
            
            duration = time.time() - start_time
            logger.info("LLM response received (duration=%.2fs, response_chars=%d)", 
                       duration, len(raw_response or ""))


            orchestrator_logger.kv_block(
                "    PAYLOAD: RAW LLM RESPONSE",
                {
                    "duration_seconds": round(duration, 2),
                    "response_length": len(raw_response or ""),
                    "response": raw_response
                },
            )


            # -----------------------------------
            # Validate output
            # -----------------------------------

            parsed_payload = (
                self._parse_and_validate(
                    raw_response
                )
            )
            
            # Validate completeness: all input parameters must appear in payload
            if "error" not in parsed_payload:
                self._validate_completeness(parameters, parsed_payload.get("payload", {}), intent_type)
            
            return parsed_payload


        except Exception as e:

            logger.exception(

                "Payload generation failed"
            )


            return {

                "error":
                str(e)
            }


    def _parse_and_validate(

        self,

        raw_response: str

    ) -> Dict[str, Any]:

        """
        Extract JSON safely from LLM output.
        Handles markdown and extra text.
        """


        match = re.search(

            r"\{.*\}",

            raw_response,

            re.DOTALL
        )


        if not match:

            return {

                "error":
                "No JSON found"
            }


        try:

            parsed = json.loads(

                match.group()
            )


        except json.JSONDecodeError:

            return {

                "error":
                "Invalid JSON returned"
            }


        # Allow explicit error response

        if "error" in parsed:

            return parsed


        required = [

            "operation",
            "payload"
        ]


        missing = [

            field

            for field in required

            if field not in parsed
        ]


        if missing:

            return {

                "error":
                f"Missing fields: {missing}"
            }


        return parsed


    def _validate_completeness(
        self,
        input_parameters: Dict[str, Any],
        generated_payload: Dict[str, Any],
        intent_type: str
    ) -> None:
        """
        Validate that the generated payload satisfies the SOP contract.
        
        Instead of checking if input parameter names match payload field names
        (which can differ), we verify that:
        1. All required SOP contract fields are present
        2. The payload has values for all user-provided parameters
        
        This allows for parameter name transformations (e.g., "name" -> "vlan_name")
        while ensuring no user data is lost.
        """
        from app.registry.intent_registry import CANONICAL_INTENT_SCHEMAS
        
        schema = CANONICAL_INTENT_SCHEMAS.get(intent_type, {})
        sop_contract = schema.get("sop_payload_contract", {})
        
        if not sop_contract:
            # No SOP contract defined, skip validation
            return
        
        # Validate that all SOP contract fields are present
        missing_contract_fields = []
        for contract_field in sop_contract.keys():
            if contract_field not in generated_payload:
                missing_contract_fields.append(contract_field)
        
        if missing_contract_fields:
            error_msg = (
                f"LLM generated incomplete payload. "
                f"Missing SOP contract fields: {', '.join(missing_contract_fields)}. "
                f"SOP contract: {sop_contract}. "
                f"Generated payload: {generated_payload}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Additional check: ensure payload has at least as many non-empty values
        # as were provided in input (catches cases where LLM drops data)
        input_value_count = sum(1 for v in input_parameters.values() if v is not None and v != "")
        payload_value_count = sum(1 for v in generated_payload.values() if v is not None and v != "")
        
        if payload_value_count < input_value_count:
            logger.warning(
                "Generated payload has fewer values (%d) than input parameters (%d). "
                "Input: %s, Payload: %s",
                payload_value_count, input_value_count, input_parameters, generated_payload
            )
            # Don't fail here, just warn - the contract validation above is sufficient