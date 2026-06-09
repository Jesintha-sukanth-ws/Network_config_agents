"""Check if operational VLAN endpoint returns system/default VLANs."""
import requests
import json
import urllib3

urllib3.disable_warnings()
AUTH = ("admin", "C1sco12345")
HOST = "https://devnetsandboxiosxec9k.cisco.com:443"
HEADERS = {"Accept": "application/yang-data+json"}

endpoints = [
    ("/restconf/data/Cisco-IOS-XE-vlan-oper:vlans", "vlan-oper"),
    ("/restconf/data/Cisco-IOS-XE-native:native/vlan", "native/vlan (config)"),
    ("/restconf/data/Cisco-IOS-XE-native:native/vlan/Cisco-IOS-XE-vlan:vlan-list", "vlan-list direct"),
]

for ep, label in endpoints:
    r = requests.get(f"{HOST}{ep}", auth=AUTH, headers=HEADERS, verify=False, timeout=30)
    print(f"\n{'='*60}")
    print(f"{label}: {ep}")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(json.dumps(data, indent=2)[:2000])
    elif r.status_code == 204:
        print("  No content (model not populated)")
    else:
        print(f"  {r.text[:200]}")

# Also try show vlan via RPC
print(f"\n{'='*60}")
print("RPC: show vlan brief (via RESTCONF RPC)")
rpc_url = f"{HOST}/restconf/operations/Cisco-IOS-XE-rpc:show"
rpc_payload = {"input": {"command": "show vlan brief"}}
r = requests.post(rpc_url, auth=AUTH, headers={**HEADERS, "Content-Type": "application/yang-data+json"}, json=rpc_payload, verify=False, timeout=30)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    print(r.json().get("Cisco-IOS-XE-rpc:output", {}).get("result", "")[:1500])
else:
    print(f"  {r.text[:300]}")

