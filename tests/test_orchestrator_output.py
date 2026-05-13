#!/usr/bin/env python3
"""
Test orchestrator with clean formatted output
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.orchestrator_service import process_task
from app.output.output_handler import print_task_result


def test_orchestrator_with_real_task():
    """Test orchestrator with a real task"""
    
    # Sample task data from ServiceNow
    task_data = {
        "number": "SCTASK0010006",
        "sys_id": "033e8d1b83204710b3df95d6feaad31f",
        "short_description": "Configure a VLAN and assign it to a switch port.",
        "description": "A new department requires network access. Create VLAN 10 and assign it to interface GigabitEthernet0/1. Ensure the port is configured in access mode.",
        "cmdb_ci": {
            "value": "0644da3883b0c310b3df95d6feaad31c"  # Nexus9000_Sandbox
        }
    }
    
    print("\n" + "=" * 120)
    print("TESTING ORCHESTRATOR WITH CLEAN OUTPUT")
    print("=" * 120)
    print("\nProcessing task with formatted output...\n")
    
    # Process the task
    result = process_task(task_data)
    
    # Print formatted output using output handler
    print_task_result(result)
    
    print("\n" + "=" * 120)
    print("✓ TEST COMPLETE")
    print("=" * 120 + "\n")


if __name__ == "__main__":
    test_orchestrator_with_real_task()
