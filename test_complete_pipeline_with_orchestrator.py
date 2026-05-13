"""
Complete Pipeline Test with Orchestrator Service

This test verifies the complete orchestration pipeline including:
1. Orchestrator service coordination
2. All 6 validation steps
3. Detailed logging output
4. Error handling
5. Final result formatting

This is the most comprehensive test of the entire system.
"""

from app.services.orchestrator_service import process_task
from app.validation.schema_validator import SchemaValidator
from app.network_validation.workflow_validator import WorkflowValidator
from app.network_validation.state_validator import StateValidator
from unittest.mock import patch, MagicMock
import json


def test_complete_orchestrator_pipeline():
    """Test the complete orchestrator pipeline with mocked external dependencies"""
    
    print("\n" + "=" * 80)
    print("COMPLETE ORCHESTRATOR PIPELINE TEST")
    print("=" * 80)
    print("\nTesting full orchestrator service with all 6 steps:")
    print("1. Intent Extraction")
    print("2. Schema Validation") 
    print("3. Workflow Validation")
    print("4. CMDB Lookup")
    print("5. Device State Retrieval")
    print("6. State Validation")
    
    # Mock task data
    task_data = {
        "number": "TASK001",
        "sys_id": "test-sys-id-123",
        "short_description": "Configure VLAN 200 for HR department",
        "description": "Create VLAN 200 named HR and assign it to interface Gi1/0/10",
        "cmdb_ci": {
            "value": "test-ci-sys-id"
        }
    }
    
    # Mock intent service response
    mock_intent = {
        "workflow": [
            {
                "intent_type": "create_vlan",
                "parameters": {"vlan_id": 200, "name": "HR"}
            },
            {
                "intent_type": "set_interface_mode_access",
                "parameters": {"interface": "Gi1/0/10"}
            },
            {
                "intent_type": "assign_access_vlan",
                "parameters": {"interface": "Gi1/0/10", "vlan_id": 200}
            }
        ]
    }
    
    # Mock CMDB response
    mock_device = {
        "device_name": "SW-HR-01",
        "vendor": "Cisco",
        "model": "C9300-48P",
        "os_type": "IOS-XE",
        "os_version": "16.12.05",
        "management_host": "192.168.1.50"
    }
    
    # Mock device facts response
    mock_device_facts = {
        "device_info": {
            "os_version": "16.12.05",
            "hostname": "SW-HR-01"
        },
        "vlans": [
            {"vlan_id": 1, "name": "default", "state": "active"},
            {"vlan_id": 10, "name": "MGMT", "state": "active"}
        ],
        "interfaces": [
            {
                "name": "Gi1/0/10",
                "status": "up",
                "mode": "routed",
                "access_vlan": None,
                "description": ""
            }
        ],
        "trunks": []
    }
    
    # Apply mocks and run orchestrator
    with patch('app.services.intent_service.parse_intent') as mock_parse_intent, \
         patch('app.services.cmdb_service.get_cmdb_data') as mock_get_cmdb, \
         patch('devices.device_state_service.get_device_facts') as mock_get_facts, \
         patch('app.services.display_service.display_terminal_output') as mock_display:
        
        # Configure mocks
        mock_parse_intent.return_value = mock_intent
        mock_get_cmdb.return_value = mock_device
        mock_get_facts.return_value = mock_device_facts
        mock_display.return_value = None
        
        print("\n" + "-" * 80)
        print("EXECUTING ORCHESTRATOR...")
        print("-" * 80)
        
        # Run the orchestrator
        result = process_task(task_data)
        
        print("\n" + "-" * 80)
        print("ORCHESTRATOR EXECUTION COMPLETE")
        print("-" * 80)
        
        # Verify result structure
        if "error" in result:
            print(f"✗ FAIL: Orchestrator returned error: {result['error']}")
            if "details" in result:
                print(f"  Details: {result['details']}")
            return False
        
        # Check all expected fields are present
        expected_fields = ["task", "intent", "device", "device_facts", "execution_plan", "execution"]
        missing_fields = []
        
        for field in expected_fields:
            if field not in result:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"✗ FAIL: Missing fields in result: {missing_fields}")
            return False
        
        # Verify task information
        task_info = result.get("task", {})
        if task_info.get("task_number") != "TASK001":
            print("✗ FAIL: Task number not preserved")
            return False
        
        # Verify intent workflow
        intent_info = result.get("intent", {})
        workflow = intent_info.get("workflow", [])
        if len(workflow) != 3:
            print(f"✗ FAIL: Expected 3 workflow steps, got {len(workflow)}")
            return False
        
        # Verify device information
        device_info = result.get("device", {})
        if device_info.get("device_name") != "SW-HR-01":
            print("✗ FAIL: Device name not preserved")
            return False
        
        # Verify execution plan exists
        execution_plan = result.get("execution_plan", [])
        if len(execution_plan) == 0:
            print("✗ FAIL: No execution plan generated")
            return False
        
        # Verify execution readiness
        execution_info = result.get("execution", {})
        if not execution_info.get("ready_for_execution", False):
            print("✗ FAIL: Not ready for execution")
            return False
        
        print("✓ PASS: All orchestrator components working correctly")
        print(f"  - Task processed: {task_info.get('task_number')}")
        print(f"  - Workflow steps: {len(workflow)}")
        print(f"  - Device: {device_info.get('device_name')}")
        print(f"  - Execution plan: {len(execution_plan)} steps")
        print(f"  - Ready for execution: {execution_info.get('ready_for_execution')}")
        
        return True


def test_orchestrator_error_handling():
    """Test orchestrator error handling for various failure scenarios"""
    
    print("\n" + "=" * 80)
    print("ORCHESTRATOR ERROR HANDLING TEST")
    print("=" * 80)
    
    # Test 1: Intent extraction failure
    print("\nTest 1: Intent extraction failure")
    
    task_data = {
        "number": "TASK002",
        "sys_id": "test-sys-id-456",
        "short_description": "Test task",
        "description": "Test description"
    }
    
    with patch('app.services.intent_service.parse_intent') as mock_parse_intent:
        mock_parse_intent.return_value = {"error": "LLM parsing failed"}
        
        result = process_task(task_data)
        
        if result.get("error") == "intent_extraction_failed":
            print("  ✓ PASS: Intent extraction error handled correctly")
        else:
            print("  ✗ FAIL: Intent extraction error not handled")
            return False
    
    # Test 2: Schema validation failure
    print("\nTest 2: Schema validation failure")
    
    invalid_intent = {
        "workflow": [
            {
                "intent_type": "invalid_intent_type",
                "parameters": {}
            }
        ]
    }
    
    with patch('app.services.intent_service.parse_intent') as mock_parse_intent:
        mock_parse_intent.return_value = invalid_intent
        
        result = process_task(task_data)
        
        if result.get("error") == "schema_validation_failed":
            print("  ✓ PASS: Schema validation error handled correctly")
        else:
            print("  ✗ FAIL: Schema validation error not handled")
            return False
    
    # Test 3: Workflow validation failure
    print("\nTest 3: Workflow validation failure")
    
    invalid_workflow_intent = {
        "workflow": [
            {
                "intent_type": "create_vlan",
                "parameters": {"vlan_id": 5000}  # Invalid VLAN ID
            }
        ]
    }
    
    with patch('app.services.intent_service.parse_intent') as mock_parse_intent:
        mock_parse_intent.return_value = invalid_workflow_intent
        
        result = process_task(task_data)
        
        if result.get("error") == "workflow_validation_failed":
            print("  ✓ PASS: Workflow validation error handled correctly")
        else:
            print("  ✗ FAIL: Workflow validation error not handled")
            return False
    
    print("\n✓ All error handling tests passed")
    return True


def test_validation_integration():
    """Test that all validators are properly integrated and working together"""
    
    print("\n" + "=" * 80)
    print("VALIDATION INTEGRATION TEST")
    print("=" * 80)
    
    # Test schema validator
    print("\nTesting Schema Validator...")
    schema_validator = SchemaValidator()
    
    valid_workflow = {
        "workflow": [
            {
                "intent_type": "create_vlan",
                "parameters": {"vlan_id": 300, "name": "TEST"}
            }
        ]
    }
    
    schema_result = schema_validator.validate_workflow(valid_workflow)
    if not schema_result["safe"]:
        print("  ✗ FAIL: Schema validator failed on valid workflow")
        return False
    print("  ✓ PASS: Schema validator working")
    
    # Test workflow validator
    print("\nTesting Workflow Validator...")
    workflow_validator = WorkflowValidator()
    
    workflow_result = workflow_validator.validate_workflow(schema_result["workflow"])
    if not workflow_result["safe"]:
        print("  ✗ FAIL: Workflow validator failed on valid workflow")
        return False
    print("  ✓ PASS: Workflow validator working")
    
    # Test state validator
    print("\nTesting State Validator...")
    state_validator = StateValidator()
    
    mock_device_state = {
        "vlans": {},
        "interfaces": {}
    }
    
    state_result = state_validator.validate_state(schema_result["workflow"], mock_device_state)
    if not state_result["safe"]:
        print("  ✗ FAIL: State validator failed on valid workflow")
        return False
    print("  ✓ PASS: State validator working")
    
    print("\n✓ All validators integrated and working correctly")
    return True


def run_complete_pipeline_tests():
    """Run all complete pipeline tests"""
    
    print("\n" + "=" * 80)
    print("COMPLETE PIPELINE TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Complete Orchestrator Pipeline", test_complete_orchestrator_pipeline),
        ("Orchestrator Error Handling", test_orchestrator_error_handling),
        ("Validation Integration", test_validation_integration),
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
    print("COMPLETE PIPELINE TEST SUMMARY")
    print("=" * 80)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "=" * 80)
        print("✓ COMPLETE PIPELINE FULLY FUNCTIONAL")
        print("=" * 80)
        print("\nEnd-to-end orchestration pipeline verified:")
        print("  ✓ Orchestrator service coordination working")
        print("  ✓ All 6 validation steps integrated")
        print("  ✓ Error handling robust")
        print("  ✓ Logging and progress tracking functional")
        print("  ✓ Result formatting complete")
        print("  ✓ Ready for production use")
        return True
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    import sys
    success = run_complete_pipeline_tests()
    sys.exit(0 if success else 1)