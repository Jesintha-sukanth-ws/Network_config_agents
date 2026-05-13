# =========================================================
# Full Orchestrator Workflow Test
# =========================================================
# Tests the complete 6-step orchestrator workflow:
# 1. Intent Extraction
# 2. Guardrails
# 3. Normalization  
# 4. CMDB Lookup
# 5. Device Facts Retrieval
# 6. Policy Engine
# =========================================================

from app.services.orchestrator_service import process_task
from app.output.output_handler import print_task_result
import json

print("=" * 80)
print("FULL ORCHESTRATOR WORKFLOW TEST")
print("=" * 80)

# =========================================================
# TEST CASE 1: Simple VLAN Configuration
# =========================================================
print("\n[TEST CASE 1] Simple VLAN Configuration")
print("-" * 80)

task_1 = {
    "task_id": "TASK001",
    "description": "Configure interface Gi1/0/5 as access port in VLAN 30",
    "device_name": "Nexus9000_Sandbox",
    "cmdb_ci": {
        "value": "test_device_sys_id_001"
    }
}

print(f"Input Task: {task_1['description']}")
print(f"Target Device: {task_1['device_name']}")

try:
    result_1 = process_task(task_1)
    
    print("\n✓ WORKFLOW COMPLETED SUCCESSFULLY")
    print("\nStep-by-Step Results:")
    
    # Step 1: Intent Extraction
    if "intent_extraction" in result_1:
        intent = result_1["intent_extraction"]
        print(f"\n[STEP 1] Intent Extraction:")
        print(f"  Workflow Steps: {len(intent.get('workflow', []))}")
        for i, step in enumerate(intent.get('workflow', []), 1):
            print(f"    {i}. {step['intent_type']}")
            if step.get('interface'):
                print(f"       Interface: {step['interface']}")
            if step.get('vlan_id'):
                print(f"       VLAN: {step['vlan_id']}")
    
    # Step 2: Guardrails
    if "guardrails" in result_1:
        guardrails = result_1["guardrails"]
        print(f"\n[STEP 2] Guardrails:")
        print(f"  Status: {guardrails.get('status', 'N/A')}")
        if guardrails.get('warnings'):
            print(f"  Warnings: {len(guardrails['warnings'])}")
    
    # Step 3: Normalization
    if "normalization" in result_1:
        norm = result_1["normalization"]
        print(f"\n[STEP 3] Normalization:")
        print(f"  Normalized Steps: {len(norm.get('workflow', []))}")
    
    # Step 4: CMDB Lookup
    if "cmdb_data" in result_1:
        cmdb = result_1["cmdb_data"]
        print(f"\n[STEP 4] CMDB Lookup:")
        print(f"  Device: {cmdb.get('device_name', 'N/A')}")
        print(f"  Vendor: {cmdb.get('vendor', 'N/A')}")
        print(f"  OS Type: {cmdb.get('os_type', 'N/A')}")
        print(f"  Management Host: {cmdb.get('management_host', 'N/A')}")
    
    # Step 5: Device Facts
    if "device_facts" in result_1:
        facts = result_1["device_facts"]
        print(f"\n[STEP 5] Device Facts:")
        if facts.get("device_info"):
            print(f"  OS Version: {facts['device_info'].get('os_version', 'N/A')}")
            print(f"  Hostname: {facts['device_info'].get('hostname', 'N/A')}")
        print(f"  VLANs: {len(facts.get('vlans', []))}")
        print(f"  Interfaces: {len(facts.get('interfaces', []))}")
        print(f"  Trunks: {len(facts.get('trunks', []))}")
    
    # Step 6: Policy Engine
    if "policy_result" in result_1:
        policy = result_1["policy_result"]
        print(f"\n[STEP 6] Policy Engine:")
        print(f"  Status: {policy.get('status', 'N/A')}")
        if policy.get('executable_commands'):
            print(f"  Executable Commands: {len(policy['executable_commands'])}")
            for i, cmd in enumerate(policy['executable_commands'][:3], 1):  # Show first 3
                print(f"    {i}. {cmd}")
            if len(policy['executable_commands']) > 3:
                print(f"    ... and {len(policy['executable_commands']) - 3} more")

except Exception as e:
    print(f"✗ WORKFLOW FAILED: {str(e)}")
    import traceback
    traceback.print_exc()

# =========================================================
# TEST CASE 2: Complex Multi-Step Workflow
# =========================================================
print("\n\n[TEST CASE 2] Complex Multi-Step Workflow")
print("-" * 80)

task_2 = {
    "task_id": "TASK002", 
    "description": "Create VLAN 100 for Finance department, configure interfaces Gi1/0/10-15 as access ports in VLAN 100, and enable portfast on all interfaces",
    "device_name": "Nexus9000_Sandbox",
    "cmdb_ci": {
        "value": "test_device_sys_id_002"
    }
}

print(f"Input Task: {task_2['description']}")
print(f"Target Device: {task_2['device_name']}")

try:
    result_2 = process_task(task_2)
    
    print("\n✓ WORKFLOW COMPLETED SUCCESSFULLY")
    
    # Show key metrics
    if "intent_extraction" in result_2:
        intent = result_2["intent_extraction"]
        print(f"\nWorkflow Complexity:")
        print(f"  Total Steps: {len(intent.get('workflow', []))}")
        
        # Count step types
        step_types = {}
        for step in intent.get('workflow', []):
            step_type = step['intent_type']
            step_types[step_type] = step_types.get(step_type, 0) + 1
        
        print(f"  Step Types:")
        for step_type, count in step_types.items():
            print(f"    - {step_type}: {count}")
    
    # Show final status
    if "policy_result" in result_2:
        policy = result_2["policy_result"]
        print(f"\nFinal Status: {policy.get('status', 'N/A')}")
        if policy.get('executable_commands'):
            print(f"Commands Generated: {len(policy['executable_commands'])}")

except Exception as e:
    print(f"✗ WORKFLOW FAILED: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("FULL ORCHESTRATOR WORKFLOW TEST COMPLETE")
print("=" * 80)