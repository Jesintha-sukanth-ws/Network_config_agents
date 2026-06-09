"""
Test device state retrieval against the Cisco DevNet Sandbox.

Connects to devnetsandboxiosxec9k.cisco.com and retrieves:
- VLANs
- Interfaces (with port mode: access/trunk)
"""

import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── Target Device ───────────────────────────────────────────────────────────

HOST = "devnetsandboxiosxec9k.cisco.com"
PORT = 443
USERNAME = "admin"
PASSWORD = "C1sco12345"
BASE_URL = f"https://{HOST}:{PORT}"

HEADERS = {"Accept": "application/yang-data+json"}
AUTH = (USERNAME, PASSWORD)
TIMEOUT = 30


def fetch(endpoint: str) -> dict:
    url = f"{BASE_URL}{endpoint}"
    print(f"\n  GET {url}")
    response = requests.get(
        url, auth=AUTH, headers=HEADERS, verify=False, timeout=TIMEOUT
    )
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Error: {response.text[:200]}")
        return {}
    return response.json()


# ─── Test 1: VLANs ──────────────────────────────────────────────────────────

print("=" * 70)
print("TEST 1: VLAN RETRIEVAL")
print("=" * 70)

vlan_data = fetch("/restconf/data/Cisco-IOS-XE-native:native/vlan")

if vlan_data:
    container = vlan_data.get("Cisco-IOS-XE-native:vlan", {})
    vlan_list = container.get("Cisco-IOS-XE-vlan:vlan-list", [])
    print(f"\n  VLANs found: {len(vlan_list)}")
    for vlan in vlan_list[:12]:
        print(f"    VLAN {vlan.get('id'):>4} - {vlan.get('name', 'unnamed')}")
    if len(vlan_list) > 12:
        print(f"    ... and {len(vlan_list) - 12} more")
else:
    print("  No VLAN data returned")


# ─── Test 2: Interfaces ─────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("TEST 2: INTERFACE RETRIEVAL")
print("=" * 70)

intf_data = fetch("/restconf/data/ietf-interfaces:interfaces")

if intf_data:
    interfaces = (
        intf_data.get("ietf-interfaces:interfaces", {}).get("interface", [])
    )
    print(f"\n  Interfaces found: {len(interfaces)}")
    for intf in interfaces[:15]:
        name = intf.get("name", "unknown")
        status = intf.get("oper-status", "unknown")
        desc = intf.get("description", "")
        print(f"    {name:<30} status={status:<6} desc={desc}")
    if len(interfaces) > 15:
        print(f"    ... and {len(interfaces) - 15} more")
else:
    print("  No interface data returned")


# ─── Test 3: Interface Switchport Mode (access/trunk) ────────────────────────

print("\n" + "=" * 70)
print("TEST 3: SWITCHPORT MODE (ACCESS/TRUNK)")
print("=" * 70)

switchport_data = fetch(
    "/restconf/data/Cisco-IOS-XE-native:native/interface"
)

if switchport_data:
    native_intf = switchport_data.get("Cisco-IOS-XE-native:interface", {})

    # Check GigabitEthernet interfaces for switchport config
    gig_interfaces = native_intf.get("GigabitEthernet", [])
    print(f"\n  GigabitEthernet interfaces: {len(gig_interfaces)}")

    for intf in gig_interfaces[:20]:
        name = intf.get("name", "?")
        switchport = intf.get("switchport", {})
        switchport_config = switchport.get(
            "Cisco-IOS-XE-switch:mode", {}
        )

        if "trunk" in switchport_config:
            mode = "trunk"
        elif "access" in switchport_config:
            mode = "access"
        elif switchport:
            mode = "switchport(default)"
        else:
            mode = "routed"

        access_vlan = (
            switchport.get("Cisco-IOS-XE-switch:access", {})
            .get("vlan", {})
            .get("vlan", "-")
        )

        print(
            f"    Gi{name:<12} mode={mode:<20} access_vlan={access_vlan}"
        )

    if len(gig_interfaces) > 20:
        print(f"    ... and {len(gig_interfaces) - 20} more")
else:
    print("  No switchport data returned")


print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
