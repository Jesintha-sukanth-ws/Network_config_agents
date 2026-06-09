"""
Test the system's DeviceStateService against the Cisco DevNet Sandbox.
Uses the actual application code path (not raw requests).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Override credentials before settings loads
os.environ["CISCO_USERNAME"] = "admin"
os.environ["CISCO_PASSWORD"] = "C1sco12345"

from app.devices.connection_service import ConnectionService
from app.devices.device_state_service import DeviceStateService


device_data = {
    "device_name": "Catalyst9000_Sandbox",
    "vendor": "Cisco",
    "model": "C9300-48P",
    "os_type": "IOS-XE",
    "management_host": "devnetsandboxiosxec9k.cisco.com",
}

conn = ConnectionService()
svc = DeviceStateService(conn)

print("=" * 70)
print("SYSTEM CODE: get_device_state(state_type='all')")
print("=" * 70)

state = svc.get_device_state(device_data, state_type="all")

# VLANs
vlans = state.get("vlans", [])
print(f"\nVLANs ({len(vlans)}):")
for v in vlans:
    print(f"  VLAN {v.get('vlan_id'):>4} - {v.get('name', '')}")

# Interfaces
interfaces = state.get("interfaces", [])
print(f"\nInterfaces ({len(interfaces)}):")
print(f"  {'Name':<30} {'Mode':<10} {'Access VLAN':<12} {'Description'}")
print(f"  {'-'*30} {'-'*10} {'-'*12} {'-'*20}")
for intf in interfaces:
    name = intf.get("name", "")
    mode = intf.get("mode", "")
    access_vlan = intf.get("access_vlan", "-")
    desc = intf.get("description", "")
    print(f"  {name:<30} {mode:<10} {str(access_vlan):<12} {desc}")

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
