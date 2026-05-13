#!/usr/bin/env python3
"""
Test to demonstrate the final formatted output
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.orchestrator_service import process_task
from app.utils.output_formatter import format_orchestrator_result


def main():
    """Test orchestrator with formatted final output"""
    
    # Sample task data
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
    print("TESTING FINAL OUTPUT FORMAT")
    print("=" * 120)
    print("\nProcessing task...\n")
    
    # Process the task (this will print the formatted output during execution)
    result = process_task(task_data)
    
    # Now show what the "Final Output" looks like
    print("\n" + "=" * 120)
    print("✓ FINAL OUTPUT (What polling service will show)")
    print("=" * 120)
    
    # This is what gets printed as the final output
    print(format_orchestrator_result(result))
    
    print("\n" + "=" * 120)
    print("NOTE: The raw dictionary is still available for programmatic use")
    print("=" * 120)
    print(f"Result type: {type(result)}")
    print(f"Result keys: {list(result.keys())}")
    print("=" * 120 + "\n")


if __name__ == "__main__":
    main()
