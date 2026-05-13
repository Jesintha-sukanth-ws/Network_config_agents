# =========================================================
# FILE: test_orchestration_reasoning.py
# PURPOSE: Test AI-native orchestration reasoning improvements
# =========================================================
from app.services.intent_service import parse_intent
import json

ORCHESTRATION_REASONING_TESTS = [
    # =====================================================
    # FLAW 1: INCONSISTENT ACCESS MODE INFERENCE
    # =====================================================
    {
        "name": "User Connectivity Implicit Access Mode #1",
        "combined_input": """Finance users connected on Gi1/0/5
should receive access to VLAN 10.""",
        "expected_intents": ["configure_access_mode", "assign_access_vlan"],
        "description": "User connectivity should imply access mode + VLAN assignment"
    },
    {
        "name": "User Connectivity Implicit Access Mode #2",
        "combined_input": """Users on Gi1/0/8 need to join VLAN 20.""",
        "expected_intents": ["configure_access_mode", "assign_access_vlan"],
        "description": "User join/access should imply access mode + VLAN assignment"
    },
    {
        "name": "User Connectivity Implicit Access Mode #3",
        "combined_input": """Configure Gi1/0/10 for HR users in VLAN 30.""",
        "expected_intents": ["configure_access_mode", "assign_access_vlan"],
        "description": "Configure for users should imply access mode + VLAN assignment"
    },
    {
        "name": "Explicit Access Port Configuration",
        "combined_input": """Configure interfaces Gi1/0/1 through Gi1/0/3
as access ports in VLAN 40.""",
        "expected_intents": ["configure_access_mode", "assign_access_vlan"],
        "description": "Explicit access port should include both steps"
    },
    {
        "name": "Simple VLAN Assignment (No Access Mode)",
        "combined_input": """Assign VLAN 50 to Gi1/0/15.""",
        "expected_intents": ["assign_access_vlan"],
        "unexpected_intents": ["configure_access_mode"],
        "description": "Simple assignment should NOT include access mode"
    },
    
    # =====================================================
    # FLAW 2: UNSUPPORTED INTENT HALLUCINATION
    # =====================================================
    {
        "name": "Spanning Tree Portfast (Not configure_spanning_tree)",
        "combined_input": """Enable fast spanning tree on Gi1/0/5.""",
        "expected_intents": ["enable_portfast"],
        "unexpected_intents": ["configure_spanning_tree"],
        "description": "Per-interface portfast should use enable_portfast, NOT configure_spanning_tree"
    },
    {
        "name": "Spanning Tree Thing (Informal)",
        "combined_input": """enable fast spanning tree thing on gi1/0/20""",
        "expected_intents": ["enable_portfast"],
        "unexpected_intents": ["configure_spanning_tree"],
        "description": "Informal spanning tree request should map to enable_portfast"
    },
    {
        "name": "Unsupported Feature - VXLAN",
        "combined_input": """Configure VXLAN overlay between switches.""",
        "expected_empty": True,
        "description": "Unsupported features should return empty workflow"
    },
    {
        "name": "Unsupported Feature - MPLS",
        "combined_input": """Enable MPLS VPN on the switch.""",
        "expected_empty": True,
        "description": "Unsupported features should return empty workflow"
    },
    
    # =====================================================
    # FLAW 3: TRUNK CONFIGURATION AMBIGUITY
    # =====================================================
    {
        "name": "Trunk Without VLANs (Omit Optional)",
        "combined_input": """Configure Gi1/0/48 as uplink trunk.""",
        "expected_intents": ["configure_trunk"],
        "check_no_null": True,
        "description": "Trunk without VLANs should omit allowed_vlans, not set to null"
    },
    {
        "name": "Trunk With VLANs (Include Optional)",
        "combined_input": """Configure trunk on Gi1/0/24 allowing VLANs 10,20,30.""",
        "expected_intents": ["configure_trunk"],
        "check_has_field": "allowed_vlans",
        "description": "Trunk with VLANs should include allowed_vlans field"
    },
    {
        "name": "VLAN Without Name (Omit Optional)",
        "combined_input": """Create VLAN 100.""",
        "expected_intents": ["create_vlan"],
        "check_no_null": True,
        "description": "VLAN without name should omit name field, not set to null"
    },
    
    # =====================================================
    # FLAW 4: WORKFLOW VERBOSITY (CONTEXT INHERITANCE)
    # =====================================================
    {
        "name": "Context Inheritance - Portfast",
        "combined_input": """Configure Gi1/0/8 for VLAN 20 and also enable portfast.""",
        "expected_intents": ["configure_access_mode", "assign_access_vlan", "enable_portfast"],
        "check_same_interface": True,
        "description": "Portfast should inherit interface context from previous operations"
    },
    {
        "name": "Context Inheritance - As Well",
        "combined_input": """Assign Gi1/0/5 to VLAN 30 and enable portfast as well.""",
        "expected_intents": ["assign_access_vlan", "enable_portfast"],
        "check_same_interface": True,
        "description": "'As well' should propagate interface context"
    },
    
    # =====================================================
    # CONSISTENCY ACROSS LANGUAGE VARIATIONS
    # =====================================================
    {
        "name": "Formal Language - User Connectivity",
        "combined_input": """Configure interface GigabitEthernet1/0/10 to provide
network access for Finance department users in VLAN 100.""",
        "expected_intents": ["configure_access_mode", "assign_access_vlan"],
        "description": "Formal language should produce consistent orchestration"
    },
    {
        "name": "Informal Language - User Connectivity",
        "combined_input": """pls make gi1/0/10 work for finance ppl in vlan 100""",
        "expected_intents": ["configure_access_mode", "assign_access_vlan"],
        "description": "Informal language should produce same orchestration as formal"
    },
    {
        "name": "Partial Language - User Connectivity",
        "combined_input": """gi1/0/10 for finance vlan 100""",
        "expected_intents": ["configure_access_mode", "assign_access_vlan"],
        "description": "Partial language should produce consistent orchestration"
    },
]

# =========================================================
# TEST RUNNER WITH VALIDATION
# =========================================================
passed = 0
failed = 0
issues = []

for index, test_case in enumerate(ORCHESTRATION_REASONING_TESTS):
    print("\n")
    print("=" * 80)
    print(f"ORCHESTRATION TEST {index + 1}: {test_case['name']}")
    print("=" * 80)
    print(f"\nDESCRIPTION: {test_case['description']}")
    print("\nINPUT:\n")
    print(test_case["combined_input"])
    print("\nOUTPUT:\n")
    
    try:
        result = parse_intent(test_case["combined_input"])
        
        if "error" in result:
            print(f"[FAIL] ERROR: {result['error']}")
            failed += 1
            issues.append(f"Test {index + 1}: Error in parsing")
            continue
        
        print(json.dumps(result, indent=2))
        
        # Validation checks
        test_passed = True
        workflow = result.get("workflow", [])
        
        # Check 1: Expected empty workflow
        if test_case.get("expected_empty"):
            if len(workflow) == 0:
                print("\n[PASS] Correctly returned empty workflow for unsupported feature")
            else:
                print(f"\n[FAIL] Expected empty workflow, got {len(workflow)} steps")
                test_passed = False
                issues.append(f"Test {index + 1}: Should return empty workflow")
        
        # Check 2: Expected intents present
        if test_case.get("expected_intents"):
            intent_types = [step["intent_type"] for step in workflow]
            for expected in test_case["expected_intents"]:
                if expected not in intent_types:
                    print(f"\n[FAIL] Missing expected intent: {expected}")
                    test_passed = False
                    issues.append(f"Test {index + 1}: Missing {expected}")
        
        # Check 3: Unexpected intents absent
        if test_case.get("unexpected_intents"):
            intent_types = [step["intent_type"] for step in workflow]
            for unexpected in test_case["unexpected_intents"]:
                if unexpected in intent_types:
                    print(f"\n[FAIL] Found unexpected intent: {unexpected}")
                    test_passed = False
                    issues.append(f"Test {index + 1}: Unexpected {unexpected}")
        
        # Check 4: No null values in parameters
        if test_case.get("check_no_null"):
            for step in workflow:
                for key, value in step.get("parameters", {}).items():
                    if value is None:
                        print(f"\n[FAIL] Found null value for parameter: {key}")
                        test_passed = False
                        issues.append(f"Test {index + 1}: Null value in {key}")
        
        # Check 5: Required field present
        if test_case.get("check_has_field"):
            field = test_case["check_has_field"]
            found = False
            for step in workflow:
                if field in step.get("parameters", {}):
                    found = True
                    break
            if not found:
                print(f"\n[FAIL] Missing required field: {field}")
                test_passed = False
                issues.append(f"Test {index + 1}: Missing field {field}")
        
        # Check 6: Same interface context inheritance
        if test_case.get("check_same_interface"):
            interfaces = []
            for step in workflow:
                if "interface" in step.get("parameters", {}):
                    interfaces.append(step["parameters"]["interface"])
            if len(set(interfaces)) > 1:
                print(f"\n[FAIL] Interface context not inherited: {interfaces}")
                test_passed = False
                issues.append(f"Test {index + 1}: Interface context broken")
        
        if test_passed:
            print("\n[PASS] All validation checks passed")
            passed += 1
        else:
            failed += 1
            
    except Exception as error:
        print(f"[FAIL] EXCEPTION: {str(error)}")
        failed += 1
        issues.append(f"Test {index + 1}: Exception - {str(error)}")
    
    print("\n")

# =========================================================
# SUMMARY
# =========================================================
print("=" * 80)
print("ORCHESTRATION REASONING TEST SUMMARY")
print("=" * 80)
print(f"Total Tests: {len(ORCHESTRATION_REASONING_TESTS)}")
print(f"[PASS] Passed: {passed}")
print(f"[FAIL] Failed: {failed}")
print(f"Success Rate: {(passed/len(ORCHESTRATION_REASONING_TESTS)*100):.1f}%")
print("=" * 80)

if issues:
    print("\nISSUES FOUND:")
    for issue in issues:
        print(f"  - {issue}")
    print("=" * 80)
