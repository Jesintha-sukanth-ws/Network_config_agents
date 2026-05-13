#!/usr/bin/env python3
"""
Test real device data retrieval and display formatted output
"""

import sys
import os
import requests
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import DEVICE_CREDENTIALS


def get_restconf_data(host, endpoint, username, password):
    """Get data from RESTCONF endpoint"""
    
    url = f"https://{host}/{endpoint}"
    
    headers = {
        "Accept": "application/yang-data+json",
        "Content-Type": "application/yang-data+json"
    }
    
    try:
        response = requests.get(
            url,
            auth=(username, password),
            headers=headers,
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Status {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def main():
    host = "devnetsandboxiosxec9k.cisco.com"
    credentials = DEVICE_CREDENTIALS["Cisco"]
    username = credentials["username"]
    password = credentials["password"]
    
    print("\n" + "=" * 120)
    print("REAL DEVICE DATA RETRIEVAL TEST")
    print("=" * 120)
    print(f"\nHost: {host}")
    
    # Get version info
    print("\n[1/3] Getting device version...")
    version_data = get_restconf_data(host, "restconf/data/Cisco-IOS-XE-native:native/version", username, password)
    
    if "error" not in version_data:
        version = version_data.get("Cisco-IOS-XE-native:version", "Unknown")
        print(f"  ✓ OS Version: {version}")
    else:
        print(f"  ✗ Failed: {version_data['error']}")
    
    # Get interfaces
    print("\n[2/3] Getting interfaces...")
    intf_data = get_restconf_data(host, "restconf/data/ietf-interfaces:interfaces", username, password)
    
    if "error" not in intf_data:
        interfaces = intf_data.get("ietf-interfaces:interfaces", {}).get("interface", [])
        print(f"  ✓ Found {len(interfaces)} interfaces")
        
        # Display formatted interface data
        print("\n" + "=" * 120)
        print("INTERFACE DATA")
        print("=" * 120)
        print(f"{'Interface':<25} {'Type':<30} {'Admin Status':<15} {'Oper Status':<15}")
        print("-" * 120)
        
        for intf in interfaces[:10]:  # Show first 10
            name = intf.get("name", "N/A")
            intf_type = intf.get("type", "N/A")
            if ":" in intf_type:
                intf_type = intf_type.split(":")[-1]
            admin_status = intf.get("enabled", False)
            admin_str = "up" if admin_status else "down"
            oper_status = intf.get("oper-status", "unknown")
            
            print(f"{name:<25} {intf_type:<30} {admin_str:<15} {oper_status:<15}")
        
        if len(interfaces) > 10:
            print(f"\n... and {len(interfaces) - 10} more interfaces")
        
        print("\n" + "=" * 120)
        
        # Show raw data for first interface
        if interfaces:
            print("\nSample Interface Data (first interface):")
            print("=" * 120)
            print(json.dumps(interfaces[0], indent=2))
            print("=" * 120)
    else:
        print(f"  ✗ Failed: {intf_data['error']}")
    
    # Get native config
    print("\n[3/3] Getting native configuration...")
    native_data = get_restconf_data(host, "restconf/data/Cisco-IOS-XE-native:native", username, password)
    
    if "error" not in native_data:
        native = native_data.get("Cisco-IOS-XE-native:native", {})
        print(f"  ✓ Native config retrieved")
        print(f"    Keys available: {list(native.keys())[:10]}")
        
        # Check for VLAN data in native config
        if "vlan" in native:
            vlans = native.get("vlan", {}).get("vlan-list", [])
            print(f"\n  VLANs in native config: {len(vlans)}")
            
            if vlans:
                print("\n" + "=" * 120)
                print("VLAN DATA (from native config)")
                print("=" * 120)
                print(f"{'VLAN ID':<10} {'Name':<30}")
                print("-" * 120)
                
                for vlan in vlans[:20]:  # Show first 20
                    vlan_id = vlan.get("id", "N/A")
                    vlan_name = vlan.get("name", "N/A")
                    print(f"{vlan_id:<10} {vlan_name:<30}")
                
                print("=" * 120)
    else:
        print(f"  ✗ Failed: {native_data['error']}")
    
    print("\n" + "=" * 120)
    print("✓ TEST COMPLETE")
    print("=" * 120 + "\n")


if __name__ == "__main__":
    main()
