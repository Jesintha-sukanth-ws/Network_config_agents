"""
Test VTP status and VLAN brief via RESTCONF CLI RPC.

Uses the IOS-XE RESTCONF CLI execution endpoint to run
show commands without hardcoding any device-specific values.
"""

import requests
import urllib3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DEVICE_CREDENTIALS, DEVICE_TIMEOUT

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── Device config (from .env via settings) ──────────────────────────────────

HOST = "devnetsandboxiosxec9k.cisco.com"
PORT = 443
USERNAME = DEVICE_CREDENTIALS.get("Cisco", {}).get("username") or "admin"
PASSWORD = DEVICE_CREDENTIALS.get("Cisco", {}).get("password") or "C1sco12345"

BASE_URL = f"https://{HOST}:{PORT}"
AUTH = (USERNAME, PASSWORD)


def run_cli_command(command: str) -> str:
    """
    Execute a CLI command on the device via RESTCONF RPC.
    Tries multiple known IOS-XE RPC endpoints for CLI execution.
    Returns the command output as a string.
    """

    headers = {
        "Accept": "application/yang-data+json",
        "Content-Type": "application/yang-data+json",
    }

  
    rpc_endpoints = [
        (
            f"{BASE_URL}/restconf/operations/cisco-ia:run-cli-command",
            {"input": {"command": command}},
        ),
        (
            f"{BASE_URL}/restconf/operations/Cisco-IOS-XE-rpc:run-cli-command",
            {"input": {"command": command}},
        ),
    ]

    for url, payload in rpc_endpoints:
        response = requests.post(
            url,
            auth=AUTH,
            headers=headers,
            json=payload,
            verify=False,
            timeout=DEVICE_TIMEOUT,
        )

        if response.status_code == 200:
            data = response.json()
            # Extract output from any key containing "output"
            for key, val in data.items():
                if isinstance(val, dict) and "result" in val:
                    return val["result"]
                if isinstance(val, str):
                    return val
            return str(data)

   
    return (
        f"CLI RPC not available on this device.\n"
        f"Last response: {response.status_code}\n"
        f"Body: {response.text[:300]}"
    )


# ─── Tests ───────────────────────────────────────────────────────────────────

print("=" * 70)
print("TEST: VTP STATUS & VLAN BRIEF")
print(f"Device: {HOST}")
print(f"Auth: {USERNAME}")
print("=" * 70)

# Test 1: show vtp status via RPC
print("\n" + "-" * 70)
print("show vtp status (via CLI RPC)")
print("-" * 70)
output = run_cli_command("show vtp status")
print(output)

# Test 2: show vlan brief via RPC
print("\n" + "-" * 70)
print("show vlan brief (via CLI RPC)")
print("-" * 70)
output = run_cli_command("show vlan brief")
print(output)

# Test 3: VTP via RESTCONF data endpoint
print("\n" + "-" * 70)
print("VTP via RESTCONF data endpoint")
print("-" * 70)
headers = {"Accept": "application/yang-data+json"}
vtp_endpoints = [
    "/restconf/data/Cisco-IOS-XE-native:native/vtp",
    "/restconf/data/Cisco-IOS-XE-vtp:vtp",
]
for ep in vtp_endpoints:
    r = requests.get(
        f"{BASE_URL}{ep}", auth=AUTH, headers=headers,
        verify=False, timeout=DEVICE_TIMEOUT
    )
    print(f"  {ep} -> {r.status_code}")
    if r.status_code == 200:
        import json
        print(json.dumps(r.json(), indent=2)[:500])

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
