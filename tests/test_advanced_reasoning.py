# =========================================================
# FILE: test_advanced_reasoning.py
# =========================================================
from app.services.intent_service import parse_intent
import json

ADVANCED_REASONING_TESTS = [
    # =====================================================
    # IMPLIED ACCESS WORKFLOW
    # =====================================================
    {
        "name": "Implied User Connectivity",
        "combined_input": """Finance users connected on Gi1/0/5
should receive access to VLAN 10."""
    },
    
    # =====================================================
    # CONTEXT PROPAGATION
    # =====================================================
    {
        "name": "Portfast Context Inheritance",
        "combined_input": """Configure Gi1/0/8 for VLAN 20
and also enable portfast."""
    },
    
    # =====================================================
    # INTERFACE RANGE UNDERSTANDING
    # =====================================================
    {
        "name": "Interface Range Expansion",
        "combined_input": """Configure interfaces Gi1/0/1 through Gi1/0/5
as access ports in VLAN 30."""
    },
    
    # =====================================================
    # NATURAL LANGUAGE VARIATION
    # =====================================================
    {
        "name": "Natural Language Networking",
        "combined_input": """Engineering department users on Gi1/0/10
need to join Engineering VLAN 40."""
    },
    
    # =====================================================
    # IMPLICIT TRUNK UNDERSTANDING
    # =====================================================
    {
        "name": "Implicit Uplink Trunk",
        "combined_input": """Prepare Gi1/0/48 as uplink interface
between switches carrying VLANs 10,20,30."""
    },
    
    # =====================================================
    # MULTI-STEP CONTEXTUAL WORKFLOW
    # =====================================================
    {
        "name": "Complex Contextual Workflow",
        "combined_input": """Create VLAN 50 named HR.
HR users connected on interfaces
Gi1/0/11 through Gi1/0/15
should receive connectivity.
Enable portfast as well."""
    },
    
    # =====================================================
    # PARTIAL HUMAN LANGUAGE
    # =====================================================
    {
        "name": "Human Informal Request",
        "combined_input": """need finance setup on gi1/0/20
make it normal user port
enable fast spanning tree thing"""
    },
    
    # =====================================================
    # MIXED OPERATIONS
    # =====================================================
    {
        "name": "Mixed Real Workflow",
        "combined_input": """Set hostname Branch_SW_05.
Create VLAN 70 named SALES.
Configure Gi1/0/5 and Gi1/0/6
for SALES users.
Configure Gi1/0/48 as uplink trunk."""
    },
    
    # =====================================================
    # AMBIGUOUS REQUEST
    # =====================================================
    {
        "name": "Ambiguous Request",
        "combined_input": """Configure office connectivity
for users on Gi1/0/9."""
    },
    
    # =====================================================
    # LONG REALISTIC REQUEST
    # =====================================================
    {
        "name": "Large Enterprise Workflow",
        "combined_input": """Configure hostname HQ_Access_SW_01.
Create VLAN 100 named Finance.
Create VLAN 200 named HR.
Create VLAN 300 named Engineering.
Assign interfaces Gi1/0/1 through Gi1/0/10
to VLAN 100.
Assign interfaces Gi1/0/11 through Gi1/0/20
to VLAN 200.
Assign interfaces Gi1/0/21 through Gi1/0/30
to VLAN 300.
Enable portfast on all user interfaces.
Configure Gi1/0/48 as trunk uplink
allowing VLANs 100,200,300
with native VLAN 999."""
    }
]

# =========================================================
# TEST RUNNER
# =========================================================
passed = 0
failed = 0

for index, test_case in enumerate(ADVANCED_REASONING_TESTS):
    print("\n")
    print("=" * 80)
    print(f"ADVANCED TEST {index + 1}: {test_case['name']}")
    print("=" * 80)
    print("\nINPUT:\n")
    print(test_case["combined_input"])
    print("\nOUTPUT:\n")
    
    try:
        result = parse_intent(test_case["combined_input"])
        
        if "error" in result:
            print(f"[FAIL] ERROR: {result['error']}")
            failed += 1
        else:
            print("[PASS] SUCCESS")
            print(json.dumps(result, indent=2))
            passed += 1
            
    except Exception as error:
        print(f"[FAIL] EXCEPTION: {str(error)}")
        failed += 1
    
    print("\n")

# =========================================================
# SUMMARY
# =========================================================
print("=" * 80)
print("ADVANCED REASONING TEST SUMMARY")
print("=" * 80)
print(f"Total Tests: {len(ADVANCED_REASONING_TESTS)}")
print(f"[PASS] Passed: {passed}")
print(f"[FAIL] Failed: {failed}")
print(f"Success Rate: {(passed/len(ADVANCED_REASONING_TESTS)*100):.1f}%")
print("=" * 80)
