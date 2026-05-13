"""
Pipeline Validation Test

This test focuses specifically on the validation pipeline components
to verify they are working correctly together without external dependencies.
"""

from app.validation.schema_validator import SchemaValidator
from app.network_validation.workflow_validator import WorkflowValidator
from app.network_validation.state_validator import StateValidator
from app.utils.logger import logger


def test_validation_pipeline_integration():
    """Test the complete validation pipeline integration"""
    
    print("\n" + "=" * 80)
    print("VALIDATION PIPELINE INTEGRATION TEST")
    print("=" * 80)
    
    # Test workflow that should pass all validations
    test_workflow = {
        "workflow": [
            {
                "intent_type": "create_vlan",
                "parameters": {"vlan_id": 150, "name": "SALES"}
            },
            {
                "intent_type": "set_interface_mode_access",
                "parameters": {"interface": "Gi1/0/15"}
            },
            {
                "intent_type": "assign_access_vlan",
                "parameters": {"interface": "Gi1/0/15", "vlan_id": 150}
            },
            {
                "intent_type": "configure_interface_description",
                "parameters": {"interface": "Gi1/0/15", "description": "Sales Department Port"}
            }
        ]
    }
    
    print(f"\nTesting workflow with {len(test_workflow['workflow'])} steps:")
    for i, step in enumerate(test_workflow['workflow'], 1):
        print(f"  {i}. {step['intent_type']} - {step['parameters']}")
    
    # Step 1: Schema Validation
    print("\n" + "-" * 60)
    print("STEP 1: SCHEMA VALIDATION")
    print("-" * 60)
    
    schema_validator = SchemaValidator()
    schema_result = schema_validator.validate_workflow(test_workflow)
    
    if not schema_result["safe"]:
        print("✗ FAIL: Schema validation failed")
        for error in schema_result["errors"]:
            print(f"  Error: {error['message']}")
        return False
    
    print("✓ PASS: Schema validation successful")
    print(f"  - Validated {len(schema_result['workflow'])} workflow steps")
    
    # Step 2: Workflow Validation
    print("\n" + "-" * 60)
    print("STEP 2: WORKFLOW VALIDATION")
    print("-" * 60)
    
    workflow_validator = WorkflowValidator()
    workflow_result = workflow_validator.validate_workflow(schema_result["workflow"])
    
    if not workflow_result["safe"]:
        print("✗ FAIL: Workflow validation failed")
        for error in workflow_result["errors"]:
            print(f"  Error: {error['message']}")
        return False
    
    print("✓ PASS: Workflow validation successful")
    print("  - VLAN ranges validated")
    print("  - Interface formats validated")
    print("  - Parameter combinations validated")
    
    # Step 3: State Validation
    print("\n" + "-" * 60)
    print("STEP 3: STATE VALIDATION")
    print("-" * 60)
    
    # Mock current device state
    current_state = {
        "vlans": {
            "1": {"name": "default"},
            "10": {"name": "MGMT"}
            # VLAN 150 doesn't exist yet - this is OK because we're creating it first
        },
        "interfaces": {
            "Gi1/0/15": {
                "mode": "routed",
                "access_vlan": None,
                "shutdown": False,
                "description": ""
            }
        }
    }
    
    state_validator = StateValidator()
    state_result = state_validator.validate_state(schema_result["workflow"], current_state)
    
    if not state_result["safe"]:
        print("✗ FAIL: State validation failed")
        for error in state_result["errors"]:
            print(f"  Error: {error['message']}")
        return False
    
    print("✓ PASS: State validation successful")
    
    execution_plan = state_result.get("execution_plan", [])
    print(f"  - Generated execution plan with {len(execution_plan)} steps")
    
    # Analyze execution plan
    execute_count = sum(1 for step in execution_plan if step.get("execute", True))
    skip_count = len(execution_plan) - execute_count
    
    print(f"  - Steps to execute: {execute_count}")
    print(f"  - Steps to skip: {skip_count}")
    
    # Show execution plan details
    for step in execution_plan:
        step_num = step.get("step")
        intent = step.get("intent_type")
        execute = step.get("execute", True)
        reason = step.get("reason", "")
        
        status = "EXECUTE" if execute else f"SKIP ({reason})"
        print(f"    Step {step_num} ({intent}): {status}")
    
    print("\n✓ COMPLETE VALIDATION PIPELINE WORKING")
    return True


def test_validation_error_detection():
    """Test that validation pipeline catches various types of errors"""
    
    print("\n" + "=" * 80)
    print("VALIDATION ERROR DETECTION TEST")
    print("=" * 80)
    
    # Test 1: Schema validation error
    print("\nTest 1: Schema validation error (unsupported intent)")
    
    invalid_schema_workflow = {
        "workflow": [
            {
                "intent_type": "unsupported_intent_type",
                "parameters": {"some_param": "value"}
            }
        ]
    }
    
    schema_validator = SchemaValidator()
    result = schema_validator.validate_workflow(invalid_schema_workflow)
    
    if result["safe"]:
        print("  ✗ FAIL: Schema validator did not catch unsupported intent")
        return False
    
    print("  ✓ PASS: Schema validator caught unsupported intent")
    print(f"    Error: {result['errors'][0]['message']}")
    
    # Test 2: Workflow validation error
    print("\nTest 2: Workflow validation error (invalid VLAN range)")
    
    invalid_workflow = {
        "workflow": [
            {
                "intent_type": "create_vlan",
                "parameters": {"vlan_id": 5000}  # Exceeds max VLAN ID
            }
        ]
    }
    
    # First pass schema validation (structure is valid)
    schema_result = schema_validator.validate_workflow(invalid_workflow)
    if not schema_result["safe"]:
        print("  ✗ FAIL: Unexpected schema validation failure")
        return False
    
    # Then test workflow validation
    workflow_validator = WorkflowValidator()
    result = workflow_validator.validate_workflow(schema_result["workflow"])
    
    if result["safe"]:
        print("  ✗ FAIL: Workflow validator did not catch invalid VLAN range")
        return False
    
    print("  ✓ PASS: Workflow validator caught invalid VLAN range")
    print(f"    Error: {result['errors'][0]['message']}")
    
    # Test 3: State validation error
    print("\nTest 3: State validation error (missing VLAN dependency)")
    
    valid_workflow = {
        "workflow": [
            {
                "intent_type": "assign_access_vlan",
                "parameters": {"interface": "Gi1/0/1", "vlan_id": 999}
            }
        ]
    }
    
    # Pass schema and workflow validation
    schema_result = schema_validator.validate_workflow(valid_workflow)
    workflow_result = workflow_validator.validate_workflow(schema_result["workflow"])
    
    if not schema_result["safe"] or not workflow_result["safe"]:
        print("  ✗ FAIL: Unexpected validation failure in setup")
        return False
    
    # Test state validation with missing VLAN
    current_state = {
        "vlans": {
            "1": {"name": "default"}
            # VLAN 999 doesn't exist
        },
        "interfaces": {
            "Gi1/0/1": {
                "mode": "access",
                "access_vlan": 1,
                "shutdown": False,
                "description": ""
            }
        }
    }
    
    state_validator = StateValidator()
    result = state_validator.validate_state(schema_result["workflow"], current_state)
    
    if result["safe"]:
        print("  ✗ FAIL: State validator did not catch missing VLAN dependency")
        return False
    
    print("  ✓ PASS: State validator caught missing VLAN dependency")
    print(f"    Error: {result['errors'][0]['message']}")
    
    print("\n✓ ALL ERROR DETECTION TESTS PASSED")
    return True


def test_validation_with_logging():
    """Test validation pipeline with detailed logging"""
    
    print("\n" + "=" * 80)
    print("VALIDATION PIPELINE WITH LOGGING TEST")
    print("=" * 80)
    
    # Test workflow
    workflow = {
        "workflow": [
            {
                "intent_type": "create_vlan",
                "parameters": {"vlan_id": 300, "name": "MARKETING"}
            },
            {
                "intent_type": "set_interface_mode_trunk",
                "parameters": {"interface": "Gi1/0/48"}
            },
            {
                "intent_type": "configure_allowed_vlans",
                "parameters": {"interface": "Gi1/0/48", "allowed_vlans": [1, 10, 300]}
            }
        ]
    }
    
    print("\nTesting with detailed logging simulation...")
    
    # Simulate orchestrator logging style
    logger.header("VALIDATION PIPELINE TEST")
    logger.subheader("Testing 3-step workflow with trunk configuration")
    
    # Schema validation with logging
    logger.step_start(1, 3, "Schema Validation")
    logger.step_progress("Checking workflow structure")
    logger.step_progress("Validating intent types")
    logger.step_progress("Checking required parameters")
    
    schema_validator = SchemaValidator()
    schema_result = schema_validator.validate_workflow(workflow)
    
    if schema_result["safe"]:
        logger.validation_passed("Schema validation", [f"Validated {len(schema_result['workflow'])} steps"])
    else:
        logger.validation_failed("Schema validation", len(schema_result['errors']), schema_result['errors'])
        return False
    
    # Workflow validation with logging
    logger.step_start(2, 3, "Workflow Validation")
    logger.step_progress("Checking VLAN ranges")
    logger.step_progress("Validating interface formats")
    logger.step_progress("Checking trunk configurations")
    
    workflow_validator = WorkflowValidator()
    workflow_result = workflow_validator.validate_workflow(schema_result["workflow"])
    
    if workflow_result["safe"]:
        logger.validation_passed("Workflow validation", [
            "All VLAN ranges valid",
            "All interface formats correct",
            "All trunk configurations valid"
        ])
    else:
        logger.validation_failed("Workflow validation", len(workflow_result['errors']), workflow_result['errors'])
        return False
    
    # State validation with logging
    logger.step_start(3, 3, "State Validation")
    logger.step_progress("Comparing desired vs current state")
    logger.step_progress("Checking idempotency")
    logger.step_progress("Building execution plan")
    
    current_state = {
        "vlans": {
            "1": {"name": "default"},
            "10": {"name": "MGMT"}
        },
        "interfaces": {
            "Gi1/0/48": {
                "mode": "access",
                "access_vlan": 1,
                "shutdown": False,
                "description": ""
            }
        }
    }
    
    state_validator = StateValidator()
    state_result = state_validator.validate_state(schema_result["workflow"], current_state)
    
    if state_result["safe"]:
        execution_plan = state_result.get("execution_plan", [])
        execute_count = sum(1 for step in execution_plan if step.get("execute", True))
        skip_count = len(execution_plan) - execute_count
        
        logger.step_success("State validation PASSED")
        logger.execution_plan(len(execution_plan), execute_count, skip_count)
    else:
        logger.validation_failed("State validation", len(state_result['errors']), state_result['errors'])
        return False
    
    logger.header("VALIDATION PIPELINE TEST COMPLETE")
    
    print("\n✓ VALIDATION PIPELINE WITH LOGGING WORKING")
    return True


def run_pipeline_validation_tests():
    """Run all pipeline validation tests"""
    
    print("\n" + "=" * 80)
    print("PIPELINE VALIDATION TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Validation Pipeline Integration", test_validation_pipeline_integration),
        ("Validation Error Detection", test_validation_error_detection),
        ("Validation with Logging", test_validation_with_logging),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ EXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("PIPELINE VALIDATION TEST SUMMARY")
    print("=" * 80)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "=" * 80)
        print("✓ VALIDATION PIPELINE FULLY FUNCTIONAL")
        print("=" * 80)
        print("\nValidation pipeline components verified:")
        print("  ✓ Schema validation working correctly")
        print("  ✓ Workflow validation catching errors")
        print("  ✓ State validation with idempotency")
        print("  ✓ Error detection comprehensive")
        print("  ✓ Logging integration functional")
        print("  ✓ All validators properly integrated")
        return True
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    import sys
    success = run_pipeline_validation_tests()
    sys.exit(0 if success else 1)