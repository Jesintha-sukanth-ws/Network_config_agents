#!/usr/bin/env python3
"""
Switch State Viewer - TEST UTILITY
===================================
Standalone test utility to retrieve and display network device state.

⚠️  THIS IS A TEST FILE - NOT INTEGRATED WITH MAIN APPLICATION CODE ⚠️

ARCHITECTURE:
User Request → CMDB Lookup → Device Metadata → Connection Manager → 
Protocol Selection → Live Device Connection → Retrieve State → Display

NO HARDCODED VALUES - All data retrieved dynamically from:
1. CMDB (device metadata)
2. Live device connection (operational state)

Usage:
    python tests/switch_state_viewer.py <ci_sys_id>
    
Example:
    python tests/switch_state_viewer.py test_device_sys_id_001
"""

import sys
import json
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import services for dynamic data retrieval
from app.services.cmdb_service import get_cmdb_data
from app.services.facts_service import get_device_facts


def format_switch_state(device_facts: Dict[str, Any], device_info: Dict[str, Any]) -> str:
   
    output = []
    
    # Header
    output.append("=" * 120)
    output.append("SWITCH STATE - DEVICE INFORMATION")
    output.append("=" * 120)
    output.append("")
    
    # Device Information from CMDB
    output.append(f"Device Name:      {device_info.get('device_name', 'N/A')}")
    output.append(f"Vendor:           {device_info.get('vendor', 'N/A')}")
    output.append(f"Model:            {device_info.get('model', 'N/A')}")
    output.append(f"OS Type:          {device_info.get('os_type', 'N/A')}")
    output.append(f"OS Version:       {device_info.get('os_version', 'N/A')}")
    output.append(f"Management Host:  {device_info.get('management_host', 'N/A')}")
    
    # Device Facts - Hostname from live device
    device_info_facts = device_facts.get('device_info', {})
    if device_info_facts and device_info_facts.get('hostname'):
        output.append(f"Hostname:         {device_info_facts.get('hostname', 'N/A')}")
    
    output.append("")
    output.append("=" * 120)
    
    # VLANs from live device
    vlans = device_facts.get('vlans', [])
    output.append(f"CONFIGURED VLANs ({len(vlans)} total)")
    output.append("-" * 120)
    
    if vlans:
        output.append(f"{'VLAN ID':<10} {'Name':<30} {'State':<15}")
        output.append("-" * 120)
        for vlan in vlans:
            vlan_id = vlan.get('vlan_id', 'N/A')
            name = vlan.get('name', 'N/A')
            state = vlan.get('state', 'N/A')
            output.append(f"{vlan_id:<10} {name:<30} {state:<15}")
    else:
        output.append("No VLANs currently configured on device")
    
    output.append("")
    
    # Interfaces from live device
    interfaces = device_facts.get('interfaces', [])
    output.append(f"INTERFACES ({len(interfaces)} total)")
    output.append("-" * 120)
    
    if interfaces:
        output.append(f"{'Interface':<20} {'VLAN':<10} {'Status':<12} {'Mode':<12} {'Description':<40}")
        output.append("-" * 120)
        
        # Display ALL interfaces with their VLAN assignments
        for intf in interfaces:
            name = intf.get('name', 'N/A')
            status = intf.get('status', 'down') if intf.get('status') else 'down'
            mode = intf.get('mode', 'access') if intf.get('mode') else 'access'
            access_vlan = intf.get('access_vlan', 1)
            description = intf.get('description', '')
            
            output.append(f"{name:<20} {str(access_vlan):<10} {status:<12} {mode:<12} {description:<40}")
    else:
        output.append("No interfaces retrieved from device")
    
    output.append("")
    
    # Trunks from live device
    trunks = device_facts.get('trunks', [])
    output.append(f"TRUNK INTERFACES ({len(trunks)} total)")
    output.append("-" * 120)
    
    if trunks:
        output.append(f"{'Interface':<20} {'Native VLAN':<15} {'Allowed VLANs':<70}")
        output.append("-" * 120)
        for trunk in trunks:
            interface = trunk.get('interface', 'N/A')
            native_vlan = trunk.get('native_vlan', 'N/A')
            allowed_vlans = trunk.get('allowed_vlans', [])
            
            # Format allowed VLANs for display
            if allowed_vlans:
                if len(allowed_vlans) > 15:
                    vlan_display = ', '.join(map(str, allowed_vlans[:15])) + f" ... ({len(allowed_vlans)} total)"
                else:
                    vlan_display = ', '.join(map(str, allowed_vlans))
            else:
                vlan_display = "None"
            
            output.append(f"{interface:<20} {str(native_vlan):<15} {vlan_display:<70}")
    else:
        output.append("No trunk interfaces currently configured on device")
    
    output.append("")
    output.append("=" * 120)
    
    return "\n".join(output)


def get_and_display_switch_state(ci_sys_id: str) -> None:
    print("\n" + "=" * 120)
    print("RETRIEVING SWITCH STATE")
    print("=" * 120)
    print("")
    
    # STEP 1: CMDB Lookup
    print(f"[1/3] Looking up device in CMDB (CI: {ci_sys_id})...")
    device = get_cmdb_data(ci_sys_id)
    
    if "error" in device:
        print(f"  ✗ CMDB lookup failed: {device['error']}")
        print("\nERROR: Cannot proceed without device metadata from CMDB")
        return
    
    print(f"  ✓ Device found: {device.get('device_name')}")
    print(f"    - Vendor: {device.get('vendor')}")
    print(f"    - Model: {device.get('model')}")
    print(f"    - OS Type: {device.get('os_type')}")
    print(f"    - Management Host: {device.get('management_host')}")
    print("")
    
    # STEP 2: Establish Connection and Retrieve Device Facts
    print(f"[2/3] Connecting to device and retrieving operational state...")
    device_facts = get_device_facts(device)
    
    if "error" in device_facts:
        print(f"  ✗ Device connection failed: {device_facts['error']}")
        print("\nERROR: Cannot retrieve device state")
        return
    
    print(f"  ✓ Device state retrieved successfully")
    print(f"    - VLANs: {len(device_facts.get('vlans', []))} configured")
    print(f"    - Interfaces: {len(device_facts.get('interfaces', []))} found")
    print(f"    - Trunks: {len(device_facts.get('trunks', []))} configured")
    print("")
    
    # STEP 3: Format and Display
    print(f"[3/3] Formatting switch state...")
    formatted_output = format_switch_state(device_facts, device)
    print("")
    print(formatted_output)
    print("")


def display_raw_json(ci_sys_id: str) -> None:
    """
    Display raw JSON of device metadata and facts.
    
    Args:
        ci_sys_id: ServiceNow Configuration Item sys_id
    """
    print("\n" + "=" * 120)
    print("RAW SWITCH STATE DATA (JSON)")
    print("=" * 120)
    print("")
    
    # CMDB Lookup
    print("DEVICE METADATA (from CMDB):")
    print("-" * 120)
    device = get_cmdb_data(ci_sys_id)
    print(json.dumps(device, indent=2))
    print("")
    
    if "error" not in device:
        # Device Facts
        print("DEVICE FACTS (from Live Device):")
        print("-" * 120)
        device_facts = get_device_facts(device)
        print(json.dumps(device_facts, indent=2))
        print("")
    
    print("=" * 120)


# Command-line interface
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n" + "=" * 120)
        print("SWITCH STATE VIEWER - TEST UTILITY")
        print("=" * 120)
        print("")
        print("⚠️  THIS IS A TEST FILE - NOT INTEGRATED WITH MAIN APPLICATION ⚠️")
        print("")
        print("This tool retrieves and displays switch state from live devices.")
        print("")
        print("ARCHITECTURE:")
        print("  User Request → CMDB Lookup → Device Metadata → Connection Manager →")
        print("  Protocol Selection → Live Device Connection → Retrieve State → Display")
        print("")
        print("USAGE:")
        print("  python tests/switch_state_viewer.py <ci_sys_id>")
        print("")
        print("ARGUMENTS:")
        print("  ci_sys_id    ServiceNow Configuration Item sys_id")
        print("")
        print("EXAMPLES:")
        print("  python tests/switch_state_viewer.py test_device_sys_id_001")
        print("  python tests/switch_state_viewer.py abc123def456ghi789")
        print("")
        print("OPTIONS:")
        print("  --json       Display raw JSON output instead of formatted view")
        print("")
        print("=" * 120)
        print("")
        sys.exit(1)
    
    ci_sys_id = sys.argv[1]
    
    # Check for JSON output flag
    if len(sys.argv) > 2 and sys.argv[2] == "--json":
        display_raw_json(ci_sys_id)
    else:
        get_and_display_switch_state(ci_sys_id)
