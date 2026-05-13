# =========================================================
# Complete Workflow Test
# =========================================================
# Tests the entire workflow from CMDB lookup to device facts
# =========================================================

from app.services.cmdb_service import get_cmdb_data
from app.services.facts_service import get_device_facts
from app.services.connection_manager import build_connection
import json

# Load capabilities from JSON
with open("device_capabilities.json", "r") as f:
    CAPABILITIES = json.load(f)

def get_device_capabilities(vendor, os_type):
    """Get capabilities from JSON file."""
    if vendor not in CAPABILITIES:
        return {"error": f"Vendor {vendor} not found"}
    if os_type not in CAPABILITIES[vendor]:
        return {"error": f"OS type {os_type} not found"}
    return CAPABILITIES[vendor][os_type]

def get_connection_url(management_host, capabilities):
    """Build connection URL."""
    port = capabilities["default_port"]
    api_path = capabilities.get("api_base_path", "")
    protocol = "https" if capabilities["preferred_connection"] in ["restconf", "nxapi_rest", "eapi"] else "ssh"
    if api_path:
        return f"{protocol}://{management_host}:{port}{api_path}"
    return f"{protocol}://{management_host}:{port}"

print("=" * 80)
print("COMPLETE WORKFLOW TEST")
print("=" * 80)

# =========================================================
# STEP 1: CMDB LOOKUP (Simulated)
# =========================================================
print("\n[STEP 1] CMDB Lookup")
print("-" * 80)

# Simulated CMDB data (in production, this comes from ServiceNow)
cmdb_device = {
    "device_name": "Nexus9000_Sandbox",
    "vendor": "Cisco",
    "model": "Nexus 9000",
    "os_type": "NX-OS",
    "os_version": "",  # Will be retrieved from device
    "management_host": "sbx-nxos-mgmt.cisco.com"  # FQDN
}

print("✓ CMDB Data Retrieved:")
for key, value in cmdb_device.items():
    print(f"  {key}: {value}")

# =========================================================
# STEP 2: CAPABILITY REGISTRY LOOKUP
# =========================================================
print("\n[STEP 2] Capability Registry Lookup")
print("-" * 80)

capabilities = get_device_capabilities(
    vendor=cmdb_device["vendor"],
    os_type=cmdb_device["os_type"]
)

print("✓ Device Capabilities:")
print(f"  Preferred Connection: {capabilities['preferred_connection']}")
print(f"  Supported Connections: {capabilities['supported_connections']}")
print(f"  Default Port: {capabilities['default_port']}")
print(f"  API Base Path: {capabilities['api_base_path']}")

# =========================================================
# STEP 3: BUILD CONNECTION URL
# =========================================================
print("\n[STEP 3] Build Connection URL")
print("-" * 80)

connection_url = get_connection_url(
    management_host=cmdb_device["management_host"],
    capabilities=capabilities
)

print(f"✓ Connection URL: {connection_url}")

# =========================================================
# STEP 4: BUILD CONNECTION DATA
# =========================================================
print("\n[STEP 4] Build Connection Data")
print("-" * 80)

try:
    connection_data = build_connection(cmdb_device)
    print("✓ Connection Data Built:")
    print(f"  Host: {connection_data['host']}")
    print(f"  Port: {connection_data['port']}")
    print(f"  Connection Method: {connection_data['connection_method']}")
    print(f"  Username: {connection_data['username']}")
except Exception as e:
    print(f"✗ Failed to build connection: {str(e)}")
    exit(1)

# =========================================================
# STEP 5: RETRIEVE DEVICE FACTS
# =========================================================
print("\n[STEP 5] Retrieve Device Facts (API-based)")
print("-" * 80)

device_facts = get_device_facts(cmdb_device)

if "error" in device_facts:
    print(f"✗ Device facts retrieval failed: {device_facts['error']}")
else:
    print("✓ Device Facts Retrieved:")
    
    # Device Info
    if device_facts.get("device_info"):
        print("\n  Device Information:")
        print(f"    OS Version: {device_facts['device_info'].get('os_version', 'N/A')}")
        print(f"    Hostname: {device_facts['device_info'].get('hostname', 'N/A')}")
    
    # VLANs
    vlans = device_facts.get("vlans", [])
    print(f"\n  VLANs: {len(vlans)} configured")
    if vlans:
        print("    Sample VLANs:")
        for vlan in vlans[:5]:  # Show first 5
            print(f"      - VLAN {vlan['vlan_id']}: {vlan['name']} ({vlan['state']})")
        if len(vlans) > 5:
            print(f"      ... and {len(vlans) - 5} more")
    
    # Interfaces
    interfaces = device_facts.get("interfaces", [])
    print(f"\n  Interfaces: {len(interfaces)} found")
    if interfaces:
        print("    Sample Interfaces:")
        for intf in interfaces[:5]:  # Show first 5
            mode = intf.get('mode', 'N/A')
            status = intf.get('status', 'N/A')
            vlan = intf.get('access_vlan', 'N/A')
            print(f"      - {intf['name']}: {mode} mode, status={status}, vlan={vlan}")
        if len(interfaces) > 5:
            print(f"      ... and {len(interfaces) - 5} more")
    
    # Trunks
    trunks = device_facts.get("trunks", [])
    print(f"\n  Trunks: {len(trunks)} configured")
    if trunks:
        print("    Trunk Interfaces:")
        for trunk in trunks:
            allowed = trunk.get('allowed_vlans', [])
            native = trunk.get('native_vlan', 'N/A')
            print(f"      - {trunk['interface']}: {len(allowed)} VLANs allowed, native={native}")

# =========================================================
# STEP 6: FINAL OUTPUT
# =========================================================
print("\n[STEP 6] Final Normalized Output")
print("-" * 80)

final_output = {
    "device": cmdb_device,
    "device_facts": device_facts,
    "connection": {
        "url": connection_url,
        "method": capabilities['preferred_connection']
    }
}

# Update OS version from device if retrieved
if device_facts.get("device_info", {}).get("os_version"):
    final_output["device"]["os_version"] = device_facts["device_info"]["os_version"]

print("✓ Complete Device State:")
print(json.dumps(final_output, indent=2))

print("\n" + "=" * 80)
print("WORKFLOW TEST COMPLETE")
print("=" * 80)
