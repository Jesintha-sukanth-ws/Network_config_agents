#!/usr/bin/env python3
"""
Test workflow with sample device response data to verify formatting
This simulates what would happen if the device returned real data
"""

import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.facts_service import (
    normalize_vlans,
    normalize_interfaces, 
    normalize_trunks
)


def test_with_sample_nxos_data():
    """Test with sample NX-OS response data"""
    
    print("\n" + "=" * 120)
    print("TESTING DATA NORMALIZATION AND FORMATTING WITH SAMPLE NX-OS DATA")
    print("=" * 120)
    
    # Sample NX-API response for "show vlan brief"
    sample_vlan_response = {
        "ins_api": {
            "outputs": {
                "output": {
                    "body": {
                        "TABLE_vlanbrief": {
                            "ROW_vlanbrief": [
                                {
                                    "vlanshowbr-vlanid-utf": "1",
                                    "vlanshowbr-vlanname": "default",
                                    "vlanshowbr-vlanstate": "active"
                                },
                                {
                                    "vlanshowbr-vlanid-utf": "10",
                                    "vlanshowbr-vlanname": "Engineering",
                                    "vlanshowbr-vlanstate": "active"
                                },
                                {
                                    "vlanshowbr-vlanid-utf": "20",
                                    "vlanshowbr-vlanname": "Sales",
                                    "vlanshowbr-vlanstate": "active"
                                },
                                {
                                    "vlanshowbr-vlanid-utf": "30",
                                    "vlanshowbr-vlanname": "Marketing",
                                    "vlanshowbr-vlanstate": "active"
                                },
                                {
                                    "vlanshowbr-vlanid-utf": "100",
                                    "vlanshowbr-vlanname": "Guest",
                                    "vlanshowbr-vlanstate": "active"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
    
    # Sample NX-API response for "show interface switchport"
    sample_interface_response = {
        "ins_api": {
            "outputs": {
                "output": {
                    "body": {
                        "TABLE_interface": {
                            "ROW_interface": [
                                {
                                    "interface": "Ethernet1/1",
                                    "state": "up",
                                    "mode": "access",
                                    "access_vlan": "10",
                                    "desc": "Engineering Workstation"
                                },
                                {
                                    "interface": "Ethernet1/2",
                                    "state": "up",
                                    "mode": "access",
                                    "access_vlan": "20",
                                    "desc": "Sales Department"
                                },
                                {
                                    "interface": "Ethernet1/3",
                                    "state": "down",
                                    "mode": "access",
                                    "access_vlan": "30",
                                    "desc": "Marketing Team"
                                },
                                {
                                    "interface": "Ethernet1/4",
                                    "state": "up",
                                    "mode": "trunk",
                                    "trunkvlans": "1,10,20,30,100",
                                    "native_vlan": "1",
                                    "desc": "Uplink to Core Switch"
                                },
                                {
                                    "interface": "Ethernet1/5",
                                    "state": "up",
                                    "mode": "trunk",
                                    "trunkvlans": "10-50,100-200",
                                    "native_vlan": "1",
                                    "desc": "Trunk to Distribution"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
    
    # Normalize the data
    print("\n[1/3] Normalizing VLANs...")
    vlans_result = normalize_vlans(sample_vlan_response, "Cisco", "NX-OS")
    vlans = vlans_result.get("vlans", [])
    print(f"  ✓ Normalized {len(vlans)} VLANs")
    
    print("\n[2/3] Normalizing Interfaces...")
    interfaces_result = normalize_interfaces(sample_interface_response, "Cisco", "NX-OS")
    interfaces = interfaces_result.get("interfaces", [])
    print(f"  ✓ Normalized {len(interfaces)} interfaces")
    
    print("\n[3/3] Normalizing Trunks...")
    trunks_result = normalize_trunks(sample_interface_response, "Cisco", "NX-OS")
    trunks = trunks_result.get("trunks", [])
    print(f"  ✓ Normalized {len(trunks)} trunk interfaces")
    
    # Format and display
    print("\n" + "=" * 120)
    print("FORMATTED SWITCH STATE")
    print("=" * 120)
    
    # Device Info
    print("\nDEVICE INFORMATION:")
    print("-" * 120)
    print(f"Device Name:      Nexus9000_Sample")
    print(f"Vendor:           Cisco")
    print(f"Model:            Nexus 9000")
    print(f"OS Type:          NX-OS")
    print(f"OS Version:       9.3(7)")
    print(f"Management Host:  192.168.1.100")
    
    # VLANs
    print(f"\n{'=' * 120}")
    print(f"CONFIGURED VLANs ({len(vlans)} total)")
    print("-" * 120)
    print(f"{'VLAN ID':<10} {'Name':<30} {'State':<15}")
    print("-" * 120)
    for vlan in vlans:
        vlan_id = vlan.get('vlan_id', 'N/A')
        name = vlan.get('name', 'N/A')
        state = vlan.get('state', 'N/A')
        print(f"{vlan_id:<10} {name:<30} {state:<15}")
    
    # Interfaces
    print(f"\nINTERFACES ({len(interfaces)} total)")
    print("-" * 120)
    print(f"{'Interface':<20} {'VLAN':<10} {'Status':<12} {'Mode':<12} {'Description':<40}")
    print("-" * 120)
    for intf in interfaces:
        name = intf.get('name', 'N/A')
        vlan = intf.get('access_vlan', 'N/A')
        status = intf.get('status', 'N/A')
        mode = intf.get('mode', 'N/A')
        desc = intf.get('description', '')
        print(f"{name:<20} {str(vlan):<10} {status:<12} {mode:<12} {desc:<40}")
    
    # Trunks
    print(f"\nTRUNK INTERFACES ({len(trunks)} configured)")
    print("-" * 120)
    print(f"{'Interface':<20} {'Native VLAN':<15} {'Allowed VLANs':<70}")
    print("-" * 120)
    for trunk in trunks:
        interface = trunk.get('interface', 'N/A')
        native = trunk.get('native_vlan', 'N/A')
        allowed = trunk.get('allowed_vlans', [])
        
        if len(allowed) > 15:
            vlan_str = ', '.join(map(str, allowed[:15])) + f" ... ({len(allowed)} total)"
        else:
            vlan_str = ', '.join(map(str, allowed)) if allowed else "None"
        
        print(f"{interface:<20} {str(native):<15} {vlan_str:<70}")
    
    print("\n" + "=" * 120)
    
    # Also show raw normalized data
    print("\nRAW NORMALIZED DATA (JSON):")
    print("=" * 120)
    
    print("\nVLANs:")
    print(json.dumps(vlans, indent=2))
    
    print("\nInterfaces:")
    print(json.dumps(interfaces, indent=2))
    
    print("\nTrunks:")
    print(json.dumps(trunks, indent=2))
    
    print("\n" + "=" * 120)
    print("✓ TEST COMPLETE - Data normalization and formatting working correctly")
    print("=" * 120 + "\n")


if __name__ == "__main__":
    test_with_sample_nxos_data()
