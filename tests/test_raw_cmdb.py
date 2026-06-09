"""
test_raw_cmdb.py

Fetches RAW data from ServiceNow CMDB — no normalization, no mapping.
Prints the exact JSON response from the API.
"""

import sys
import json
import requests

sys.path.insert(0, r"c:\Users\Jesintha\Documents\Internal - Copy")

from config.settings import (
    SERVICENOW_INSTANCE,
    SERVICENOW_USERNAME,
    SERVICENOW_PASSWORD,
    SERVICENOW_SSL_VERIFY,
    SERVICENOW_TIMEOUT,
    CMDB_TABLE,
    NETWORK_GROUP_ID,
)


def fetch_raw_cmdb(ci_sys_id: str) -> dict:
    """Fetch raw CMDB record — no processing, no coercion."""

    base_url = SERVICENOW_INSTANCE.rstrip("/")
    auth = (SERVICENOW_USERNAME, SERVICENOW_PASSWORD)

    url = f"{base_url}/api/now/table/{CMDB_TABLE}/{ci_sys_id}"

    params = {
        "sysparm_display_value": "all",
    }

    print(f"\n{'='*60}")
    print(f"REQUEST URL: {url}")
    print(f"TABLE: {CMDB_TABLE}")
    print(f"CI SYS_ID: {ci_sys_id}")
    print(f"{'='*60}\n")

    response = requests.get(
        url,
        auth=auth,
        params=params,
        verify=SERVICENOW_SSL_VERIFY,
        timeout=SERVICENOW_TIMEOUT,
    )

    print(f"STATUS CODE: {response.status_code}")
    print(f"{'='*60}\n")

    if response.status_code != 200:
        print(f"ERROR: {response.text}")
        return {}

    raw = response.json()
    return raw


def fetch_all_network_devices() -> list:
    """Fetch ALL network devices from CMDB table — raw, no filtering."""

    base_url = SERVICENOW_INSTANCE.rstrip("/")
    auth = (SERVICENOW_USERNAME, SERVICENOW_PASSWORD)

    url = f"{base_url}/api/now/table/{CMDB_TABLE}"

    params = {
        "sysparm_display_value": "all",
        "sysparm_limit": 10,  # limit to 10 for readability
    }

    # If there's a network group filter, add it
    if NETWORK_GROUP_ID:
        params["sysparm_query"] = f"assignment_group={NETWORK_GROUP_ID}"

    print(f"\n{'='*60}")
    print(f"FETCHING ALL DEVICES (limit 10)")
    print(f"URL: {url}")
    print(f"TABLE: {CMDB_TABLE}")
    if NETWORK_GROUP_ID:
        print(f"NETWORK_GROUP_ID filter: {NETWORK_GROUP_ID}")
    print(f"{'='*60}\n")

    response = requests.get(
        url,
        auth=auth,
        params=params,
        verify=SERVICENOW_SSL_VERIFY,
        timeout=SERVICENOW_TIMEOUT,
    )

    print(f"STATUS CODE: {response.status_code}")

    if response.status_code != 200:
        print(f"ERROR: {response.text}")
        return []

    raw = response.json()
    results = raw.get("result", [])
    print(f"RECORDS RETURNED: {len(results)}")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":

    print("\n" + "#"*60)
    print("# RAW CMDB DATA DUMP — NO NORMALIZATION")
    print("#"*60)

    # --- Fetch all devices first ---
    devices = fetch_all_network_devices()

    if devices:
        print("\n--- RAW RECORDS ---\n")
        for i, device in enumerate(devices):
            print(f"\n{'─'*60}")
            print(f"DEVICE #{i+1}")
            print(f"{'─'*60}")
            print(json.dumps(device, indent=2, default=str))

        # Also fetch the first device individually to show single-record format
        first_sys_id = None
        if isinstance(devices[0], dict):
            sys_id_field = devices[0].get("sys_id")
            if isinstance(sys_id_field, dict):
                first_sys_id = sys_id_field.get("value")
            elif isinstance(sys_id_field, str):
                first_sys_id = sys_id_field

        if first_sys_id:
            print(f"\n\n{'#'*60}")
            print(f"# SINGLE DEVICE FETCH (sys_id: {first_sys_id})")
            print(f"{'#'*60}")
            single = fetch_raw_cmdb(first_sys_id)
            print(json.dumps(single, indent=2, default=str))
    else:
        print("\nNo devices found with group filter. Trying without filter...")

        # Try without the group filter
        base_url = SERVICENOW_INSTANCE.rstrip("/")
        auth = (SERVICENOW_USERNAME, SERVICENOW_PASSWORD)
        url = f"{base_url}/api/now/table/{CMDB_TABLE}"
        params = {
            "sysparm_display_value": "all",
            "sysparm_limit": 5,
        }

        response = requests.get(
            url,
            auth=auth,
            params=params,
            verify=SERVICENOW_SSL_VERIFY,
            timeout=SERVICENOW_TIMEOUT,
        )

        print(f"STATUS (no filter): {response.status_code}")
        if response.status_code == 200:
            raw = response.json()
            results = raw.get("result", [])
            print(f"RECORDS: {len(results)}\n")
            for i, device in enumerate(results):
                print(f"\n{'─'*60}")
                print(f"DEVICE #{i+1}")
                print(f"{'─'*60}")
                print(json.dumps(device, indent=2, default=str))
        else:
            print(f"ERROR: {response.text}")
