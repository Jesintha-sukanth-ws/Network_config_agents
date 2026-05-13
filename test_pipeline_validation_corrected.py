"""
Corrected Pipeline Validation Test

This test properly validates the pipeline components understanding that:
1. State validator checks against current device state
2. VLAN dependencies are correctly validated
3. Workflow ordering matters for dependencies
"""

from app.validation.schema_validator import SchemaValidator
from app.network_validation.workflow_validator import WorkflowValidator
from app.network_validation.state_validator import StateValidator
from app.utils.logger import logger


def test_validation_pipeline_integration():
    """Test the complete validation pipeline integration with proper dependency handling"""
    
    print("\n" + "=" * 80)
    print("VALIDATION PIPELINE INTEGRATION TEST")
    print("=" * 80)
    
    # Test 1: Simple workflow without dependencies
    print("\nTest 1: Simple workflow (create VLAN only)")
    
    simple_workflow = {
        "workflow": [
            {
                "intent_type": "create_vlan",
                "parameters": {"vlan_id": 150, "name": "SALES"}
            }
        ]
    }
    
    current_state = {
        "vlans": {
            "1": {"name": "default"},
            "10": {"name": "MGMT"}
        },
        "interfaces": {}
    }
    
    # Schema validation
    schema_validator = SchemaValidator()
    schema_result = schema_validator.validate_workflow(simple_workflow)
    
    if not schema_result["safe"]:
        print("✗ FAIL: Schema validation failed")
        return False
    print("  ✓ Schema validation passed")
    
    # Workflow validation
    workflow_validator = WorkflowValidator()
    workflow_result = workflow_validator.validate_workflow(schema_result["workflow"])
    
    if not workflow_result["safe"]:
        print("✗ FAIL: Workflow validation failed")
        return False
    print("  ✓ Workflow validation passed")
    
    # State validation
    state_validator = StateValidator()
    state_result = state_validator.validate_state(schema_result["workflow"], current_state)
    
    if not state_result["safe"]:
        print("✗ FAIL: State validation failed")
        return False
    print("  ✓ State validation passed")
    
    execution_plan = state_result.get("execution_plan", [])
    print(f"  ✓ Execution plan: {len(execution_plan)} steps")
    
    # Test 2: Workflow with existing VLAN assignment
    print("\nTest 2: Interface configuration with existing VLAN")
    
    interface_workflow = {
        "workflow": [
            {
                "intent_type": "set_interface_mode_access",
                "parameters": {"interface": "Gi1/0/5"}
            },
            {
                "intent_type": "assign_access_vlan",
                "parameters": {"interface": "Gi1/0/5", "vlan_id": 10}  # VLAN 10 exists
            }
        ]
    }
    
    current_state_with_vlan = {
        "vlans": {
            "1": {"name": "default"},
            "10": {"name": "MGMT"}  # VLAN 10 exists
        },
        "interfaces": {
            "Gi1/0/5": {
                "mode": "routed",
                "access_vlan": None,
                "shutdown": False,
                "description": ""
            }
        }
    }
    
    # Validate the workflow
    schema_result = schema_validator.validate_workflow(interface_workflow)
    workflow_result = workflow_validator.validate_workflow(schema_result["workflow"])
    state_result = state_validator.validate_state(schema_result["workflow"], current_state_with_vlan)
    
    if not schema_result["safe"] or not workflow_result["safe"] or not state_result["safe"]:
        print("✗ FAIL: Interface workflow validation failed")
        if not state_result["safe"]:
            for error in state_result["errors"]:
                print(f"    Error: {error['message']}")
        return False
    
    print("  ✓ Interface workflow validation passed")
    
    execution_plan = state_result.get("execution_plan", [])
    execute_count = sum(1 for step in execution_plan if step.get("execute", True))
    print(f"  ✓ Execution plan: {execute_count}/{len(execution_plan)} steps to execute")
    
    # Test 3: Dependency validation (should fail correctly)
    print("\nTest 3: Dependency validation (VLAN doesn't exist)")
    
    dependency_workflow = {
        "workflow": [
            {
                "intent_type": "assign_access_vlan",
                "parameters": {"interface": "Gi1/0/5", "vlan_id": 999}  # VLAN 999 doesn't exist
            }
        ]
    }
    
    schema_result = schema_validator.validate_workflow(dependency_workflow)
    workflow_result = workflow_validator.validate_workflow(schema_result["workflow"])
    state_result = state_validator.validate_state(schema_result["workflow"], current_state_with_vlan)
    
    if state_result["safe"]:
        print("✗ FAIL: State validator should have caught missing VLAN dependency")
        return False
    
    print("  ✓ State validator correctly caught missing VLAN dependency")
    print(f"    Error: {state_result['errors'][0]['message']}")
    
    print("\n✓ VALIDATION PIPELINE INTEGRATION WORKING CORRECTLY")
    return True


def test_validation_error_detection():
    """Test comprehensive error detection across all validators"""
    
    print("\n" + "=" * 80)
    print("VALIDATION ERROR DETECTION TEST")
    print("=" * 80)
    
    schema_validator = SchemaValidator()
    workflow_validator = WorkflowValidator()
    state_validator = StateValidator()
    
    # Test 1: Schema errors
    print("\nTest 1: Schema validation errors")
    
    schema_errors = [
        {
            "name": "Missing workflow field",
            "workflow": {"invalid": "structure"},
            "expected_error": "missing_workflow"
        },
        {
            "name": "Unsupported intent type",
            "workflow": {"workflow": [{"intent_type": "invalid_intent", "parameters": {}}]},
            "expected_error": "unsupported_intent"
        },
        {
            "name": "Missing required parameter",
            "workflow": {"workflow": [{"intent_type": "create_vlan", "parameters": {}}]},
            "expected_error": "missing_parameter"
        }
    ]
    
    for test_case in schema_errors:
        result = schema_validator.validate_workflow(test_case["workflow"])
        if result["safe"]:
            print(f"  ✗ FAIL: {test_case['name']} not detected")
            return False
        print(f"  ✓ PASS: {test_case['name']} detected")
    
    # Test 2: Workflow validation errors
    print("\nTest 2: Workflow validation errors")
    
    workflow_errors = [
        {
            "name": "Invalid VLAN range",
            "workflow": [{"intent_type": "create_vlan", "parameters": {"vlan_id": 5000}}],
            "expected_error": "vlan_id exceeds valid range"
        },
        {
            "name": "Invalid interface format",
            "workflow": [{"intent_type": "set_interface_mode_access", "parameters": {"interface": "InvalidInterface"}}],
            "expected_error": "invalid Cisco interface format"
        }
    ]
    
    for test_case in workflow_errors:
        result = workflow_validator.validate_workflow(test_case["workflow"])
        if result["safe"]:
            print(f"  ✗ FAIL: {test_case['name']} not detected")
            return False
        print(f"  ✓ PASS: {test_case['name']} detected")
    
    # Test 3: State validation errors
    print("\nTest 3: State validation errors")
    
    current_state = {
        "vlans": {"1": {"name": "default"}},
        "interfaces": {"Gi1/0/1": {"mode": "access", "access_vlan": 1}}
    }
    
    state_errors = [
        {
            "name": "Missing VLAN dependency",
            "workflow": [{"intent_type": "assign_access_vlan", "parameters": {"interface": "Gi1/0/1", "vlan_id": 999}}],
            "expected_error": "VLAN 999 does not exist"
        }
    ]
    
    for test_case in state_errors:
        result = state_validator.validate_state(test_case["workflow"], current_state)
        if result["safe"]:
            print(f"  ✗ FAIL: {test_case['name']} not detected")
            return False
        print(f"  ✓ PASS: {test_case['name']} detected")
    
    print("\n✓ ALL ERROR DETECTION TESTS PASSED")
    return True


def test_idempotency_detection():
    """Test that state validator correctly detects already-configured items"""
    
    print("\n" + "=" * 80)
    print("IDEMPOTENCY DETECTION TEST")
    print("=" * 80)
    
    state_validator = StateValidator()
    
    # Test 1: VLAN already exists
    print("\nTest 1: Create VLAN that already exists")
    
    workflow = [{"intent_type": "create_vlan", "parameters": {"vlan_id": 100, "name": "EXISTING"}}]
    
    current_state = {
        "vlans": {"100": {"name": "EXISTING"}},  # VLAN already exists
        "interfaces": {}
    }
    
    result = state_validator.validate_state(workflow, current_state)
    
    if not result["safe"]:
        print("✗ FAIL: State validation should pass but recommend skipping")
        return False
    
    execution_plan = result.get("execution_plan", [])
    if len(execution_plan) == 0 or execution_plan[0].get("execute", True):
        print("✗ FAIL: Should recommend skipping existing VLAN creation")
        return False
    
    print("  ✓ PASS: Correctly detected existing VLAN")
    print(f"    Reason: {execution_plan[0].get('reason')}")
    
    # Test 2: Interface already in correct mode
    print("\nTest 2: Set interface mode that's already configured")
    
    workflow = [{"intent_type": "set_interface_mode_access", "parameters": {"interface": "Gi1/0/1"}}]
    
    current_state = {
        "vlans": {},
        "interfaces": {"Gi1/0/1": {"mode": "access"}}  # Already in access mode
    }
    
    result = state_validator.validate_state(workflow, current_state)
    execution_plan = result.get("execution_plan", [])
    
    if len(execution_plan) == 0 or execution_plan[0].get("execute", True):
        print("✗ FAIL: Should recommend skipping interface mode change")
        return False
    
    print("  ✓ PASS: Correctly detected existing interface mode")
    print(f"    Reason: {execution_plan[0].get('reason')}")
    
    print("\n✓ IDEMPOTENCY DETECTION WORKING CORRECTLY")
    return True


def test_logging_integration():
    """Test that logging works correctly with validation pipeline"""
    
    print("\n" + "=" * 80)
    print("LOGGING INTEGRATION TEST")
    print("=" * 80)
    
    # Test the logger with validation pipeline
    workflow = {
        "workflow": [
            {
                "intent_type": "create_vlan",
                "parameters": {"vlan_id": 200, "name": "MARKETING"}
            }
        ]
    }
    
    current_state = {"vlans": {}, "interfaces": {}}
    
    print("\nTesting validation pipeline with logging...")
    
    # Simulate orchestrator-style logging
    logger.header("VALIDATION PIPELINE TEST")
    logger.subheader("Testing single VLAN creation workflow")
    
    # Schema validation with logging
    logger.step_start(1, 3, "Schema Validation")
    logger.step_progress("Checking workflow structure")
    logger.step_progress("Validating intent types")
    logger.step_progress("Checking parameters")
    
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
    logger.step_progress("Validating parameters")
    
    workflow_validator = WorkflowValidator()
    workflow_result = workflow_validator.validate_workflow(schema_result["workflow"])
    
    if workflow_result["safe"]:
        logger.validation_passed("Workflow validation", ["All VLAN ranges valid"])
    else:
        logger.validation_failed("Workflow validation", len(workflow_result['errors']), workflow_result['errors'])
        return False
    
    # State validation with logging
    logger.step_start(3, 3, "State Validation")
    logger.step_progress("Comparing desired vs current state")
    logger.step_progress("Building execution plan")
    
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
    
    print("\n✓ LOGGING INTEGRATION WORKING CORRECTLY")
    return True


def run_corrected_pipeline_tests():
    """Run all corrected pipeline validation tests"""
    
    print("\n" + "=" * 80)
    print("CORRECTED PIPELINE VALIDATION TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Validation Pipeline Integration", test_validation_pipeline_integration),
        ("Validation Error Detection", test_validation_error_detection),
        ("Idempotency Detection", test_idempotency_detection),
        ("Logging Integration", test_logging_integration),
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
    print("CORRECTED PIPELINE TEST SUMMARY")
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
        print("\nEnd-to-end validation pipeline verified:")
        print("  ✓ Schema validation working correctly")
        print("  ✓ Workflow validation catching network errors")
        print("  ✓ State validation with proper dependency checking")
        print("  ✓ Idempotency detection working")
        print("  ✓ Error detection comprehensive")
        print("  ✓ Logging integration functional")
        print("  ✓ All validators properly integrated")
        print("\n🎉 THE ORCHESTRATION PIPELINE IS WORKING PERFECTLY!")
        return True
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    import sys
    success = run_corrected_pipeline_tests()
    sys.exit(0 if success else 1)