"""
Test file for SchemaValidator and intent prompt integration
"""

from app.validation.schema_validator import SchemaValidator
from app.registry.switch_intent_schema_registry import SWITCH_INTENT_SCHEMAS
from app.prompts.intent_prompt import SYSTEM_PROMPT
import json

def run_tests():
    validator = SchemaValidator()

    # =============================================
    # Test 1: Valid workflow with alias
    # =============================================
    test_workflow_1 = {
        "workflow": [
            {
                "intent_type": "access_port",  # alias for set_interface_mode_access
                "parameters": {"interface": "Gi1/0/5"}
            },
            {
                "intent_type": "assign_vlan",  # alias for assign_access_vlan
                "parameters": {"interface": "Gi1/0/5", "vlan_id": 10}
            }
        ]
    }

    result1 = validator.validate_workflow(test_workflow_1)
    print("\n=== Test 1: Alias Resolution & Valid Workflow ===")
    print(json.dumps(result1, indent=2))

    # =============================================
    # Test 2: Missing required parameter
    # =============================================
    test_workflow_2 = {
        "workflow": [
            {
                "intent_type": "create_vlan",
                "parameters": {}  # missing vlan_id
            }
        ]
    }

    result2 = validator.validate_workflow(test_workflow_2)
    print("\n=== Test 2: Missing Required Parameter ===")
    print(json.dumps(result2, indent=2))

    # =============================================
    # Test 3: Unknown parameter
    # =============================================
    test_workflow_3 = {
        "workflow": [
            {
                "intent_type": "set_hostname",
                "parameters": {"hostname": "Branch_SW_01", "location": "HQ"}  # location is unknown
            }
        ]
    }

    result3 = validator.validate_workflow(test_workflow_3)
    print("\n=== Test 3: Unknown Parameter ===")
    print(json.dumps(result3, indent=2))

    # =============================================
    # Test 4: Invalid parameter type
    # =============================================
    test_workflow_4 = {
        "workflow": [
            {
                "intent_type": "create_vlan",
                "parameters": {"vlan_id": "Ten"}  # should be int
            }
        ]
    }

    result4 = validator.validate_workflow(test_workflow_4)
    print("\n=== Test 4: Invalid Parameter Type ===")
    print(json.dumps(result4, indent=2))

    # =============================================
    # Test 5: Unsupported intent
    # =============================================
    test_workflow_5 = {
        "workflow": [
            {
                "intent_type": "enable_vxlan",
                "parameters": {}
            }
        ]
    }

    result5 = validator.validate_workflow(test_workflow_5)
    print("\n=== Test 5: Unsupported Intent ===")
    print(json.dumps(result5, indent=2))


if __name__ == "__main__":
    print("SYSTEM_PROMPT:\n")
    print(SYSTEM_PROMPT[:1000] + "\n...")  # print first 1000 chars for brevity
    run_tests()