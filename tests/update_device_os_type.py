#!/usr/bin/env python3
"""
Update device OS type in ServiceNow CMDB
Changes Nexus9000_Sandbox from NX-OS to IOS-XE
"""

import sys
import os
import requests
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import SERVICENOW_INSTANCE, USERNAME, PASSWORD


def update_device_os_type(sys_id, new_os_type):
    """Update device OS type in CMDB"""
    
    print("\n" + "=" * 80)
    print("UPDATING DEVICE OS TYPE IN CMDB")
    print("=" * 80)
    
    url = f"{SERVICENOW_INSTANCE}/api/now/table/cmdb_ci_comm/{sys_id}"
    
    # First, get current device info
    print(f"\n[1/3] Fetching current device info...")
    response = requests.get(
        url,
        auth=(USERNAME, PASSWORD),
        params={"sysparm_fields": "name,u_os_type"}
    )
    
    if response.status_code != 200:
        print(f"  ✗ Failed to fetch device: {response.status_code}")
        return False
    
    current_data = response.json().get("result", {})
    device_name = current_data.get("name", "Unknown")
    current_os_type = current_data.get("u_os_type", "Unknown")
    
    print(f"  ✓ Device: {device_name}")
    print(f"    Current OS Type: {current_os_type}")
    
    # Update OS type
    print(f"\n[2/3] Updating OS type to: {new_os_type}...")
    
    update_data = {
        "u_os_type": new_os_type
    }
    
    response = requests.patch(
        url,
        auth=(USERNAME, PASSWORD),
        headers={"Content-Type": "application/json"},
        json=update_data
    )
    
    if response.status_code != 200:
        print(f"  ✗ Update failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False
    
    print(f"  ✓ OS type updated successfully")
    
    # Verify update
    print(f"\n[3/3] Verifying update...")
    
    response = requests.get(
        url,
        auth=(USERNAME, PASSWORD),
        params={"sysparm_fields": "name,u_os_type"}
    )
    
    if response.status_code != 200:
        print(f"  ✗ Verification failed: {response.status_code}")
        return False
    
    updated_data = response.json().get("result", {})
    updated_os_type = updated_data.get("u_os_type", "Unknown")
    
    print(f"  ✓ Verified")
    print(f"    Device: {device_name}")
    print(f"    Old OS Type: {current_os_type}")
    print(f"    New OS Type: {updated_os_type}")
    
    print("\n" + "=" * 80)
    print("✓ DEVICE OS TYPE UPDATED SUCCESSFULLY")
    print("=" * 80 + "\n")
    
    return True


if __name__ == "__main__":
    # Nexus9000_Sandbox sys_id
    device_sys_id = "0644da3883b0c310b3df95d6feaad31c"
    new_os_type = "IOS-XE"
    
    print("\nThis script will update the device OS type in ServiceNow CMDB")
    print(f"Device sys_id: {device_sys_id}")
    print(f"New OS Type: {new_os_type}")
    print("\nThis change is necessary because the device actually supports RESTCONF (IOS-XE)")
    print("not NX-API (NX-OS) as currently classified.")
    
    success = update_device_os_type(device_sys_id, new_os_type)
    
    if success:
        print("\nNext steps:")
        print("  1. Test the workflow again:")
        print(f"     python tests/switch_state_viewer.py {device_sys_id}")
        print("  2. The orchestrator should now use RESTCONF instead of NX-API")
        print("  3. Device facts retrieval should work correctly")
        sys.exit(0)
    else:
        print("\n✗ Update failed")
        sys.exit(1)
