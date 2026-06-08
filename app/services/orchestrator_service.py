from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, cast

from app.services.intent_service import IntentService
from app.services.cmdb_service import CMDBService
from app.services.policy_resolver import PolicyResolver

from app.validation.schema_validator import SchemaValidator
from app.network_validation.workflow_validator import WorkflowValidator
from app.network_validation.state_validator import StateValidator
from app.workflow.dependency_planner import DependencyPlanner

from app.devices.connection_service import ConnectionService
from app.devices.device_state_service import DeviceStateService

from app.rag.chroma_manager import ChromaManager
from app.rag.embedding_service import EmbeddingService
from app.rag.retrieval_service import RetrievalService
from app.llm.ollama_client import OllamaClient
from app.llm.payload_generation_service import PayloadGenerationService

from app.execution.push_config import PushConfigExecutor
from app.execution.execution_status import ExecutionStatusVerifier
from app.registry.intent_registry import CANONICAL_INTENT_SCHEMAS
from app.services.display_service import display_terminal_output
from app.utils.logger import orchestrator_logger

logger = logging.getLogger(__name__)

# Singleton allocations
_intent_service = IntentService()
_cmdb_service = CMDBService()
_policy_resolver = PolicyResolver()
_schema_validator = SchemaValidator()
_workflow_validator = WorkflowValidator()
_state_validator = StateValidator()
_dependency_planner = DependencyPlanner()
_executor = PushConfigExecutor()

_connection_service = None
_device_service = None
_payload_service = None

def _get_connection_service() -> ConnectionService:
    global _connection_service
    if _connection_service is None:
        _connection_service = ConnectionService()
    return _connection_service

def _get_device_service() -> DeviceStateService:
    global _device_service
    if _device_service is None:
        _device_service = DeviceStateService(_get_connection_service())
    return _device_service

def _get_payload_service() -> PayloadGenerationService:
    global _payload_service
    if _payload_service is None:
        logger.info("Initializing RAG and LLM services...")
        _payload_service = PayloadGenerationService(
            retrieval_service=RetrievalService(ChromaManager(), EmbeddingService()),
            llm_client=OllamaClient(),
        )
    return _payload_service

def _get_verifier() -> ExecutionStatusVerifier:
    return ExecutionStatusVerifier()

def plan_task(task: Dict[str, Any]) -> Dict[str, Any]:
    task_id = task.get("number", "unknown")
    orchestrator_logger.header(f"PLANNING TASK {task_id}")
    
    description = (task.get("description") or task.get("short_description") or "").strip()
    if not description:
        raise ValueError("Task description missing")

    orchestrator_logger.kv_block("[1/9] TASK DESCRIPTION", {"task_number": task_id, "description": description})

    workflow = _intent_service.parse(description)
    orchestrator_logger.kv_block("[2/9] LLM-EXTRACTED INTENT WORKFLOW", workflow)

    schema_result = _schema_validator.validate_workflow(workflow)
    orchestrator_logger.kv_block("[3/9] SCHEMA VALIDATION", {
        "safe": schema_result.get("safe"),
        "errors": schema_result.get("errors", []),
        "normalized_workflow": schema_result.get("workflow", []),
    })

    if not schema_result.get("safe"):
        return {"safe": False, "status": "rejected", "message": "Schema validation failed", "errors": schema_result.get("errors", [])}

    cmdb_ci_raw = task.get("cmdb_ci")
    cmdb_id = cmdb_ci_raw.get("value") if isinstance(cmdb_ci_raw, dict) else cmdb_ci_raw
    if not cmdb_id:
        raise ValueError("CMDB CI missing")
        
    device = _cmdb_service.get_cmdb_data(cmdb_id)
    device_data = device.model_dump() if hasattr(device, "model_dump") else device

    orchestrator_logger.kv_block("[4/9] CMDB LOOKUP", device_data)
    policy = _policy_resolver.resolve(cast(Dict[str, Any], device_data))
    orchestrator_logger.kv_block("[5/9] RESOLVED POLICY", policy)

    workflow_result = _workflow_validator.validate_workflow(workflow.get("workflow", []), policy)
    orchestrator_logger.kv_block("[6/9] WORKFLOW VALIDATION", {"safe": workflow_result.get("safe"), "errors": workflow_result.get("errors", [])})

    if not workflow_result.get("safe"):
        return {"safe": False, "status": "rejected", "message": "Workflow validation failed", "errors": workflow_result.get("errors", [])}

    raw_workflow = workflow.get("workflow", [])

    return {
        "safe": True,
        "device_data": device_data,
        "policy": policy,
        "ordered_workflow": raw_workflow,
        "raw_workflow": raw_workflow
    }

def prepare_change(plan_context: Dict[str, Any], task_id: str = "unknown") -> Dict[str, Any]:
    device_data = plan_context["device_data"]
    policy = plan_context["policy"]
    raw_workflow = plan_context.get("raw_workflow", plan_context["ordered_workflow"])

    current_state = _get_device_service().get_device_state(device_data, state_type="all")
    orchestrator_logger.kv_block("[7/10] LIVE DEVICE FACTS", current_state)

    dependency_result = _dependency_planner.plan(raw_workflow, current_state)
    provided_capabilities = dependency_result.get("provided_capabilities", set())
    ordered_workflow = dependency_result.get("ordered_workflow", raw_workflow)

    orchestrator_logger.kv_block("[8/10] DEPENDENCY PLANNING", {
        "valid": dependency_result.get("valid"),
        "reordered": dependency_result.get("reordered"),
        "errors": dependency_result.get("errors", []),
        "dependency_graph": dependency_result.get("dependency_graph", {}),
    })

    if not dependency_result.get("valid"):
        return {"safe": False, "errors": dependency_result.get("errors", []), "message": "Dependency resolution failed"}

    state_result = _state_validator.validate_state(ordered_workflow, current_state, provided_capabilities)
    execution_plan = state_result.get("execution_plan", [])
    verification_plan = state_result.get("verification_plan", [])

    orchestrator_logger.kv_block("[9/10] STATE VALIDATION & EXECUTION PLAN", {
        "safe": state_result.get("safe"),
        "errors": state_result.get("errors", []),
        "summary": state_result.get("summary", {}),
        "execution_plan": execution_plan,
    })

    if not state_result.get("safe"):
        return {"safe": False, "errors": state_result.get("errors", []), "message": "State verification failed pre-flight"}

    # Idempotency evaluation: check if any steps need execution
    steps_to_execute = [step for step in execution_plan if step.get("execute", True)]
    
    if not steps_to_execute:
        # All steps are idempotent - no implementation needed
        return {
            "safe": True,
            "idempotent": True,
            "task_number": task_id,
            "device_data": device_data,
            "policy": policy,
            "device_state": current_state,
            "execution_plan": execution_plan,
            "generated_payloads": [],
            "verification_plan": verification_plan,
            "message": "Pre-change validation determined that the requested configuration already exists on the target device. No implementation actions were required."
        }

    generated_payloads = []
    connection_data = _get_connection_service().connect(device_data)
    device_capability = connection_data.get("capability", {})
    device_os_version = current_state.get("device_info", {}).get("os_version", "")

    for step in steps_to_execute:
        intent_type = step.get("intent_type")
        intent_schema = CANONICAL_INTENT_SCHEMAS.get(intent_type, {})
        rag_type = intent_schema.get("rag_type", intent_type)

        payload_device = {
            "vendor": device_data.get("vendor", ""),
            "os": device_data.get("os_type", ""),
            "version": device_os_version,
            "capability": device_capability
        }

        payload = _get_payload_service().generate({
            "intent_type": intent_type,
            "rag_type": rag_type,
            "parameters": step.get("parameters", {}),
            "device": payload_device
        })

        if not isinstance(payload, dict) or "operation" not in payload or "payload" not in payload:
             return {"safe": False, "message": "Payload validation failed", "errors": [f"Step {step.get('step')}: Invalid payload."]}

        generated_payloads.append({
            "step": step.get("step"),
            "intent_type": intent_type,
            "parameters": step.get("parameters", {}),
            "payload_data": payload
        })

    return {
        "safe": True,
        "idempotent": False,
        "task_number": task_id,
        "device_data": device_data,
        "policy": policy,
        "device_state": current_state,
        "execution_plan": execution_plan,
        "generated_payloads": generated_payloads,
        "verification_plan": verification_plan,
    }

def implement_change(prepared_context: Dict[str, Any]) -> Dict[str, Any]:
    task_id = prepared_context.get("task_number", "unknown")
    device_data = prepared_context["device_data"]
    policy = prepared_context["policy"]
    current_state = prepared_context.get("device_state", {})
    execution_plan = prepared_context["execution_plan"]
    generated_payloads = prepared_context["generated_payloads"]

    results = []
    completed_intents = set()
    payload_map = {p["step"]: p["payload_data"] for p in generated_payloads}

    orchestrator_logger.kv_block("[10/10] EXECUTION PHASE", f"{len(execution_plan)} step(s) bound from local cache payload state.")

    for step in execution_plan:
        step_idx = step.get("step")
        if not step.get("execute", True):
            continue

        intent_type = step.get("intent_type")
        payload = payload_map.get(step_idx)
        
        try:
            push = _executor.execute(payload, device_data)
            verify = _get_verifier().verify(push, device_data, payload)
            results.append({
                "step": step_idx,
                "operation": intent_type,
                "parameters": step.get("parameters", {}),
                "push": push,
                "verify": verify,
                "status": "success" if verify.get("verified", False) else "failed"
            })
        except Exception as e:
            logger.exception("Execution missed at step %s", step_idx)
            results.append({"step": step_idx, "operation": intent_type, "parameters": step.get("parameters", {}), "status": "failed", "error": str(e)})

    failed = any(r.get("status") == "failed" for r in results)
    final_result = {
        "task_number": task_id,
        "device": device_data,
        "policy": policy,
        "device_state": current_state,
        "results": results,
        "status": "partial_failure" if failed else "success"
    }
    display_terminal_output(final_result)
    return final_result

def execute_plan(plan_context: Dict[str, Any], task_id: str = "unknown") -> Dict[str, Any]:
    """Retained for complete backwards compatibility."""
    prepared = prepare_change(plan_context, task_id=task_id)
    if not prepared.get("safe", True):
        return {"status": "rejected", "message": prepared.get("message", "Validation failed"), "errors": prepared.get("errors", [])}
    
    # Handle idempotent case
    if prepared.get("idempotent", False):
        return {
            "task_number": task_id,
            "device": prepared["device_data"],
            "policy": prepared["policy"],
            "device_state": prepared["device_state"],
            "results": [],
            "status": "idempotent",
            "message": prepared.get("message", "No changes required - configuration already exists")
        }
    
    return implement_change(prepared)

def process_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Retained for complete backwards compatibility."""
    task_id = task.get("number", "unknown")
    try:
        plan_context = plan_task(task)
        if not plan_context.get("safe", True):
            return plan_context
        return execute_plan(plan_context, task_id=task_id)
    except Exception as e:
        logger.exception("Task processing failed")
        return {"task_number": task_id, "status": "error", "message": str(e)}