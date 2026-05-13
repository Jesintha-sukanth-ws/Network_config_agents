# =========================================================
# FILE: test_intent_workflows.py
# =========================================================
from app.services.intent_service import parse_intent
import json

TEST_CASES = [
    {
        "name": "Simple VLAN Creation",
        "combined_input": """Create Finance VLAN
Create VLAN 10 named Finance on the Cisco Catalyst switch for the finance department."""
    },
    {
        "name": "Delete VLAN",
        "combined_input": """Remove old VLAN
Delete VLAN 55 from the switch because it is no longer required."""
    },
    {
        "name": "Access Port Configuration",
        "combined_input": """Assign user port to VLAN
Configure interface GigabitEthernet1/0/10 as an access port and assign VLAN 20."""
    },
    {
        "name": "HR Workstation Port",
        "combined_input": """Configure HR workstation port
Assign interface Gi1/0/5 to VLAN 20 for HR users and enable switchport mode access."""
    },
    {
        "name": "Trunk Configuration",
        "combined_input": """Configure uplink trunk
Configure Gi1/0/24 as a trunk port allowing VLANs 10,20,30 and set native VLAN 99."""
    },
    {
        "name": "PortFast Configuration",
        "combined_input": """Enable PortFast
Enable spanning-tree portfast on interface Gi1/0/3."""
    },
    {
        "name": "Shutdown Interface",
        "combined_input": """Shutdown unused port
Disable interface GigabitEthernet1/0/40 because it is unused."""
    },
    {
        "name": "Enable Interface",
        "combined_input": """Enable switch port
Bring interface Gi1/0/15 back online."""
    },
    {
        "name": "Interface Description",
        "combined_input": """Set uplink description
Configure interface Gi1/0/24 description as Uplink_To_Core."""
    },
    {
        "name": "Hostname Configuration",
        "combined_input": """Update switch hostname
Set the switch hostname to Branch_SW_01."""
    },
    {
        "name": "Complex Department Setup",
        "combined_input": """Configure new department network
Create VLAN 50 named Accounts.
Configure interfaces Gi1/0/10 through Gi1/0/15
as access ports in VLAN 50.
Enable portfast on all interfaces."""
    },
    {
        "name": "Branch Switch Setup",
        "combined_input": """New branch switch setup
Configure hostname Branch_SW_02.
Create VLANs 10,20,30 and configure
Gi1/0/24 as trunk allowing those VLANs
with native VLAN 99."""
    },
    {
        "name": "Mixed Access and Trunk",
        "combined_input": """Configure access and trunk ports
Assign Gi1/0/1 to VLAN 10,
Gi1/0/2 to VLAN 20,
and configure Gi1/0/48 as trunk
allowing VLANs 10 and 20."""
    },
    {
        "name": "Messy User Request",
        "combined_input": """Messy user request
pls setup vlan10 for finance users
and make gi1/0/5 access mode
also enable port fast"""
    },
    {
        "name": "Mixed Capitalization",
        "combined_input": """Mixed capitalization
CREATE vlan 60 Name SALES
and Assign gi1/0/9."""
    },
    {
        "name": "Implicit Workflow",
        "combined_input": """Implicit workflow request
Users on interface Gi1/0/7
should be part of VLAN 70."""
    },
    {
        "name": "Policy Violation VLAN 1",
        "combined_input": """Restricted VLAN assignment
Assign interface Gi1/0/10 to VLAN 1."""
    },
    {
        "name": "Invalid VLAN Name",
        "combined_input": """Invalid VLAN name
Create VLAN 80 named Finance@Dept."""
    },
    {
        "name": "Unsupported Feature",
        "combined_input": """Unsupported feature
Configure VXLAN overlay between switches."""
    },
    {
        "name": "Hallucination Test",
        "combined_input": """Unknown networking concept
Enable quantum routing optimization on Gi1/0/1."""
    }
]

# =========================================================
# RUN TESTS
# =========================================================
passed = 0
failed = 0

for index, test_case in enumerate(TEST_CASES):
    print("\n")
    print("=" * 80)
    print(f"TEST {index + 1}: {test_case['name']}")
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
print("TEST SUMMARY")
print("=" * 80)
print(f"Total Tests: {len(TEST_CASES)}")
print(f"[PASS] Passed: {passed}")
print(f"[FAIL] Failed: {failed}")
print(f"Success Rate: {(passed/len(TEST_CASES)*100):.1f}%")
print("=" * 80)
