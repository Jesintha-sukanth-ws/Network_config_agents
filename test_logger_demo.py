"""
Demo of Centralized Orchestration Logger

Shows how the logger provides clean, consistent progress messages
"""

from app.utils.logger import logger

print("\n" + "=" * 80)
print("CENTRALIZED LOGGER DEMONSTRATION")
print("=" * 80)

# Simulate orchestration flow
logger.header("ORCHESTRATOR: Processing Task TASK001")
logger.subheader("TASK DESCRIPTION:\nCreate VLAN 100 and assign to interface Gi1/0/5")

# Step 1: Intent Extraction
logger.step_start(1, 6, "Extracting Intent")
logger.step_success("Intent extracted")

# Step 2: Schema Validation
logger.step_start(2, 6, "Validating Schema")
logger.step_progress("Checking workflow structure")
logger.step_progress("Validating intent types")
logger.step_progress("Checking required parameters")
logger.step_progress("Validating parameter datatypes")
logger.validation_passed(
    "Schema validation",
    ["Validated 3 workflow step(s)"]
)

# Step 3: Workflow Validation
logger.step_start(3, 6, "Validating Workflow")
logger.step_progress("Checking VLAN ranges (1-4094)")
logger.step_progress("Validating interface formats")
logger.step_progress("Checking trunk configurations")
logger.step_progress("Validating VLAN names")
logger.validation_passed(
    "Workflow validation",
    [
        "All VLAN ranges valid",
        "All interface formats correct",
        "All trunk configurations valid"
    ]
)

# Step 4: CMDB Lookup
logger.step_start(4, 6, "Looking up Device")
logger.step_success("Device details retrieved")
logger.step_detail("Device Name     : SWITCH-01")
logger.step_detail("Vendor          : Cisco")
logger.step_detail("Model           : Catalyst 9300")
logger.step_detail("Management Host : 10.1.1.1")
logger.step_detail("OS Type         : IOS-XE")

# Step 5: Device Facts
logger.step_start(5, 6, "Retrieving Device Facts")
logger.step_success("Device facts retrieved")

# Step 6: State Validation
logger.step_start(6, 6, "Validating State")
logger.step_progress("Comparing desired state vs current state")
logger.step_progress("Checking for idempotency violations")
logger.step_progress("Validating VLAN dependencies")
logger.step_progress("Building execution plan")
logger.step_success("State validation PASSED")

# Execution plan
logger.execution_plan(
    total_steps=3,
    execute_count=2,
    skip_count=1,
    skip_reasons=["Step 1: VLAN 100 already exists"]
)

logger.header("ORCHESTRATOR: Task TASK001 Complete")

print("\n" + "=" * 80)
print("BENEFITS OF CENTRALIZED LOGGER:")
print("=" * 80)
print("1. Clean orchestrator code - no print() statements cluttering logic")
print("2. Consistent formatting - all messages follow same pattern")
print("3. Easy to modify - change logging format in one place")
print("4. Detailed progress - users see exactly what's happening")
print("5. Error context - validation failures show specific errors")
print("6. Execution planning - clear indication of what will execute/skip")
print("=" * 80)
