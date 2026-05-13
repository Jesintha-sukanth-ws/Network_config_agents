#!/usr/bin/env python3
"""
Test RESTCONF endpoints to find what's available on the device
"""

import sys
import os
import requests
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import DEVICE_CREDENTIALS


def test_restconf_endpoint(host, endpoint, username, password):
    """Test a specific RESTCONF endpoint"""
    
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
            timeout=10
        )
        
        return {
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "data": response.json() if response.status_code == 200 else response.text[:200]
        }
    except Exception as e:
        return {
            "status_code": None,
            "success": False,
            "error": str(e)
        }


def main():
    host = "devnetsandboxiosxec9k.cisco.com"
    credentials = DEVICE_CREDENTIALS["Cisco"]
    username = credentials["username"]
    password = credentials["password"]
    
    print("\n" + "=" * 80)
    print("TESTING RESTCONF ENDPOINTS")
    print("=" * 80)
    print(f"\nHost: {host}")
    print(f"Username: {username}")
    
    # Test various RESTCONF endpoints
    endpoints = [
        "restconf",
        "restconf/data",
        "restconf/data/ietf-interfaces:interfaces",
        "restconf/data/Cisco-IOS-XE-native:native",
        "restconf/data/Cisco-IOS-XE-native:native/version",
        "restconf/data/Cisco-IOS-XE-vlan-oper:vlans",
        "restconf/data/ietf-yang-library:yang-library",
        "restconf/data/netconf-state",
    ]
    
    print("\n" + "-" * 80)
    print("Testing endpoints...")
    print("-" * 80)
    
    results = []
    
    for endpoint in endpoints:
        print(f"\nTesting: /{endpoint}")
        result = test_restconf_endpoint(host, endpoint, username, password)
        
        if result["success"]:
            print(f"  ✓ SUCCESS (200)")
            if isinstance(result["data"], dict):
                keys = list(result["data"].keys())
                print(f"    Keys: {keys[:5]}")
        else:
            status = result.get("status_code", "ERROR")
            print(f"  ✗ FAILED ({status})")
            if "error" in result:
                print(f"    Error: {result['error'][:100]}")
        
        results.append({
            "endpoint": endpoint,
            "result": result
        })
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    successful = [r for r in results if r["result"]["success"]]
    failed = [r for r in results if not r["result"]["success"]]
    
    print(f"\n✓ Successful: {len(successful)}/{len(results)}")
    for r in successful:
        print(f"  - /{r['endpoint']}")
    
    if failed:
        print(f"\n✗ Failed: {len(failed)}/{len(results)}")
        for r in failed:
            status = r["result"].get("status_code", "ERROR")
            print(f"  - /{r['endpoint']} ({status})")
    
    print("\n" + "=" * 80 + "\n")
    
    # Show sample data from first successful endpoint
    if successful:
        print("Sample data from first successful endpoint:")
        print("=" * 80)
        sample = successful[0]
        print(f"Endpoint: /{sample['endpoint']}")
        print(json.dumps(sample["result"]["data"], indent=2)[:1000])
        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
