#!/usr/bin/env python3
"""
Fetch real devices from ServiceNow CMDB
"""

import sys
import os
import json
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import SERVICENOW_INSTANCE, USERNAME, PASSWORD


def fetch_all_devices():
    """Fetch all network devices from CMDB"""
    
    print("\n" + "=" * 80)
    print("FETCHING REAL DEVICES FROM SERVICENOW CMDB")
    print("=" * 80)
    
    try:
        url = f"{SERVICENOW_INSTANCE}/api/now/table/cmdb_ci_comm"
        
        params = {
            "sysparm_fields": "sys_id,name,model_number,ip_address,fqdn,u_os_type,u_os_version,manufacturer",
            "sysparm_limit": 10
        }
        
        print(f"\nConnecting to: {SERVICENOW_INSTANCE}")
        print(f"Fetching devices from: cmdb_ci_comm table")
        
        response = requests.get(
            url,
            auth=(USERNAME, PASSWORD),
            params=params
        )
        
        response.raise_for_status()
        data = response.json()
        
        devices = data.get("result", [])
        
        if not devices:
            print("\n⚠️  No devices found in CMDB")
            return []
        
        print(f"\n✓ Found {len(devices)} device(s)")
        print("\n" + "=" * 80)
        print("AVAILABLE DEVICES:")
        print("=" * 80)
        
        for idx, device in enumerate(devices, 1):
            sys_id = device.get("sys_id", "N/A")
            name = device.get("name", "N/A")
            model = device.get("model_number", "N/A")
            ip = device.get("ip_address", "N/A")
            fqdn = device.get("fqdn", "N/A")
            os_type = device.get("u_os_type", "N/A")
            
            print(f"\n[{idx}] Device: {name}")
            print(f"    sys_id: {sys_id}")
            print(f"    Model: {model}")
            print(f"    IP: {ip}")
            print(f"    FQDN: {fqdn}")
            print(f"    OS Type: {os_type}")
        
        print("\n" + "=" * 80)
        print("\nTo test with a device, run:")
        print(f"  python tests/switch_state_viewer.py <sys_id>")
        print("\nExample:")
        if devices:
            print(f"  python tests/switch_state_viewer.py {devices[0].get('sys_id')}")
        print("=" * 80 + "\n")
        
        return devices
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ CMDB connection failed: {str(e)}")
        return []
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return []


if __name__ == "__main__":
    devices = fetch_all_devices()
    
    if devices:
        sys.exit(0)
    else:
        sys.exit(1)
