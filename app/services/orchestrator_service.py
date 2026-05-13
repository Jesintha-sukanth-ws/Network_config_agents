# Orchestrator service to manage workflow pipeline

from app.services.intent_service import parse_intent
from app.services.cmdb_service import get_cmdb_data
from devices.device_state_service import get_device_facts
from app.services.display_service import display_terminal_output
from app.validation.schema_validator import SchemaValidator
from app.network_validation.workflow_validator import WorkflowValidator
from app.network_validation.state_validator import StateValidator
from app.utils.logger import logger


schema_validator = SchemaValidator()
workflow_validator = WorkflowValidator()
state_validator = StateValidator()


def process_task(
    task_data: dict
):

    task_number = task_data.get(
        "number"
    )

    task_sys_id = task_data.get(
        "sys_id"
    )

    short_desc = task_data.get(
        "short_description",
        ""
    ).strip()

    long_desc = task_data.get(
        "description",
        ""
    ).strip()

    if short_desc and long_desc:

        combined_description = (
            f"{short_desc}. {long_desc}"
        )

    else:

        combined_description = (
            short_desc or long_desc
        )

    if not combined_description:

        return {
            "error": "no_description"
        }

    # =====================================================
    # HEADER
    # =====================================================

    logger.header(f"ORCHESTRATOR: Processing Task {task_number}")
    logger.subheader(f"TASK DESCRIPTION:\n{combined_description}")

    # =====================================================
    # STEP 1 — INTENT EXTRACTION
    # =====================================================

    logger.step_start(1, 6, "Extracting Intent")

    intent = parse_intent(combined_description)

    if "error" in intent:
        logger.step_failure("Intent extraction failed")
        return {
            "error": "intent_extraction_failed",
            "details": intent["error"]
        }

    logger.step_success("Intent extracted")

    # =====================================================
    # STEP 2 — SCHEMA VALIDATION
    # =====================================================

    logger.step_start(2, 6, "Validating Schema")
    logger.step_progress("Checking workflow structure")
    logger.step_progress("Validating intent types")
    logger.step_progress("Checking required parameters")
    logger.step_progress("Validating parameter datatypes")

    schema_result = schema_validator.validate_workflow(intent)

    if not schema_result["safe"]:
        logger.validation_failed(
            "Schema validation",
            len(schema_result['errors']),
            schema_result['errors']
        )
        return {
            "error": "schema_validation_failed",
            "details": schema_result["errors"]
        }

    logger.validation_passed(
        "Schema validation",
        [f"Validated {len(schema_result.get('workflow', []))} workflow step(s)"]
    )

    # =====================================================
    # STEP 3 — WORKFLOW VALIDATION
    # =====================================================

    logger.step_start(3, 6, "Validating Workflow")
    logger.step_progress("Checking VLAN ranges (1-4094)")
    logger.step_progress("Validating interface formats")
    logger.step_progress("Checking trunk configurations")
    logger.step_progress("Validating VLAN names")

    workflow_result = workflow_validator.validate_workflow(
        schema_result.get("workflow", [])
    )

    if not workflow_result["safe"]:
        logger.validation_failed(
            "Workflow validation",
            len(workflow_result['errors']),
            workflow_result['errors']
        )
        return {
            "error": "workflow_validation_failed",
            "details": workflow_result["errors"]
        }

    logger.validation_passed(
        "Workflow validation",
        [
            "All VLAN ranges valid",
            "All interface formats correct",
            "All trunk configurations valid"
        ]
    )

    # =====================================================
    # STEP 4 — CMDB LOOKUP
    # =====================================================

    logger.step_start(4, 6, "Looking up Device")

    device = {"error": "No CI specified"}
    ci_sys_id = None
    cmdb_ci = task_data.get("cmdb_ci")

    if cmdb_ci and isinstance(cmdb_ci, dict):
        ci_sys_id = cmdb_ci.get("value")

    if ci_sys_id:
        device = get_cmdb_data(ci_sys_id)

        if "error" in device:
            logger.step_failure("CMDB lookup failed")
        else:
            logger.step_success("Device details retrieved")
            logger.step_detail(f"Device Name     : {device.get('device_name')}")
            logger.step_detail(f"Vendor          : {device.get('vendor')}")
            logger.step_detail(f"Model           : {device.get('model')}")
            logger.step_detail(f"Management Host : {device.get('management_host')}")
            logger.step_detail(f"OS Type         : {device.get('os_type')}")
    else:
        logger.step_failure("No Configuration Item found")

    # =====================================================
    # STEP 5 — DEVICE FACTS
    # =====================================================

    logger.step_start(5, 6, "Retrieving Device Facts")

    device_facts = {}

    if "error" not in device and device.get("management_host"):
        device_facts = get_device_facts(device)

        if "error" in device_facts:
            logger.step_failure(f"Device facts retrieval failed: {device_facts['error']}")
            logger.step_info("Check credentials and RESTCONF/NX-API")
        else:
            logger.step_success("Device facts retrieved")

            # Update device info
            device_info = device_facts.get("device_info", {})
            if device_info.get("hostname"):
                device["hostname"] = device_info["hostname"]
            if device_info.get("os_version"):
                device["os_version"] = device_info["os_version"]

            # Formatted output
            logger.format_device_summary(device_facts)
            logger.format_vlan_summary(device_facts)
            logger.format_interface_summary(device_facts)
            logger.format_trunk_summary(device_facts)
    else:
        logger.step_failure("Skipping device facts retrieval")

    # =====================================================
    # STEP 6 — STATE VALIDATION
    # =====================================================

    logger.step_start(6, 6, "Validating State")
    logger.step_progress("Comparing desired state vs current state")
    logger.step_progress("Checking for idempotency violations")
    logger.step_progress("Validating VLAN dependencies")
    logger.step_progress("Building execution plan")

    execution_plan = []

    if "error" not in device_facts and device_facts:
        try:
            state_result = state_validator.validate_state(
                schema_result.get("workflow", []),
                device_facts
            )

            if not state_result["safe"]:
                logger.validation_failed(
                    "State validation",
                    len(state_result['errors']),
                    state_result['errors']
                )
                return {
                    "error": "state_validation_failed",
                    "details": state_result["errors"]
                }

            logger.step_success("State validation PASSED")

            execution_plan = state_result.get("execution_plan", [])

            # Show execution plan summary
            execute_count = sum(1 for step in execution_plan if step.get("execute", True))
            skip_count = len(execution_plan) - execute_count

            skip_reasons = []
            if skip_count > 0:
                for step in execution_plan:
                    if not step.get("execute", True):
                        reason = step.get("reason", "Unknown")
                        skip_reasons.append(f"Step {step.get('step')}: {reason}")

            logger.execution_plan(
                len(execution_plan),
                execute_count,
                skip_count,
                skip_reasons if skip_reasons else None
            )

        except Exception as e:
            logger.step_failure(f"State validation ERROR: {str(e)}")

    else:
        logger.step_failure("Skipping state validation (no device facts)")

    # =====================================================
    # FINAL RESULT
    # =====================================================

    result = {

        "task": {

            "task_number":
                task_number,

            "sys_id":
                task_sys_id,

            "description":
                combined_description
        },

        "intent": {

            "workflow":
                schema_result.get(
                    "workflow",
                    []
                )
        },

        "device":
            device,

        "device_facts":
            device_facts,

        "execution_plan":
            execution_plan,

        "execution": {

            "ready_for_execution":
                True,

            "warnings": []
        }
    }

    # =====================================================
    # FOOTER
    # =====================================================

    logger.header(f"ORCHESTRATOR: Task {task_number} Complete")

    # =====================================================
    # DISPLAY FINAL OUTPUT
    # =====================================================

    display_terminal_output(result)

    return result