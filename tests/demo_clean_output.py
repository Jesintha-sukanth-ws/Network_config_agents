#!/usr/bin/env python3
"""
Demo: Clean formatted output vs raw JSON dump
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.output_formatter import print_orchestrator_result


def demo_clean_vs_raw():
    """Demonstrate clean output vs raw JSON"""
    
    # Sample orchestrator result
    sample_result = {
        "task": {
            "task_number": "SCTASK0010006",
            "sys_id": "033e8d1b83204710b3df95d6feaad31f",
            "description": "Configure a VLAN and assign it to a switch port. A new department requires network access. Create VLAN 10 and assign it to interface GigabitEthernet0/1. Ensure the port is configured in access mode."
        },
        "intent": {
            "workflow": [
                {
                    "intent_type": "create_vlan",
                    "parameters": {"vlan_id": 10}
                },
                {
                    "intent_type": "configure_access_mode",
                    "parameters": {"interface": "Gi0/1"}
                },
                {
                    "intent_type": "assign_access_vlan",
                    "parameters": {"interface": "Gi0/1", "vlan_id": 10}
                }
            ]
        },
        "device": {
            "device_name": "Nexus9000_Sandbox",
            "vendor": "Cisco",
            "model": "Nexus9000",
            "os_type": "IOS-XE",
            "os_version": "17.15",
            "management_host": "devnetsandboxiosxec9k.cisco.com"
        },
        "device_facts": {
            "device_info": {"os_version": "17.15"},
            "vlans": [],
            "interfaces": [
                {"name": "GigabitEthernet0/0", "status": "up", "mode": "routed", "access_vlan": None, "description": "DO NOT TOUCH"},
                {"name": "GigabitEthernet1/0/1", "status": "down", "mode": "routed", "access_vlan": None, "description": ""},
                {"name": "GigabitEthernet1/0/2", "status": "down", "mode": "routed", "access_vlan": None, "description": ""},
            ],
            "trunks": []
        },
        "execution": {
            "ready_for_execution": True,
            "warnings": []
        }
    }
    
    print("\n" + "=" * 120)
    print("COMPARISON: RAW JSON vs CLEAN FORMATTED OUTPUT")
    print("=" * 120)
    
    # Show raw JSON (what you had before)
    print("\n❌ OLD WAY - RAW JSON DUMP:")
    print("=" * 120)
    print(json.dumps(sample_result, indent=2)[:500] + "\n... (truncated)")
    
    # Show clean formatted output (new way)
    print("\n✅ NEW WAY - CLEAN FORMATTED OUTPUT:")
    print_orchestrator_result(sample_result)
    
    print("\n" + "=" * 120)
    print("BENEFITS OF CLEAN OUTPUT:")
    print("=" * 120)
    print("✓ Easy to read and understand")
    print("✓ Organized into logical sections")
    print("✓ Highlights important information")
    print("✓ Shows only relevant data")
    print("✓ Professional presentation")
    print("✓ No need to parse JSON manually")
    print("=" * 120 + "\n")


if __name__ == "__main__":
    demo_clean_vs_raw()
