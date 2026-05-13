"""
Connection Service - Device connection handling and protocol selection
"""

import json
import requests
from config.settings import DEVICE_CREDENTIALS

# Load capability registry
with open("devices/device_capabilities.json", "r") as f:
    CAPABILITIES = json.load(f)


def resolve_capability(vendor, os_type):
    """
    Resolve device capabilities based on vendor and OS type.
    
    Args:
        vendor: Device vendor (e.g., "Cisco")
        os_type: Operating system type (e.g., "NX-OS", "IOS-XE")
    
    Returns:
        dict: Device capability configuration
    """
    vendor_data = CAPABILITIES.get(vendor)

    if not vendor_data:
        raise Exception(f"No capability found for vendor: {vendor}")

    os_data = vendor_data.get(os_type)

    if not os_data:
        raise Exception(f"No capability found for OS: {os_type}")

    return os_data


def build_connection(device):
    """
    Build connection data for device communication.
    
    Args:
        device: Device metadata from CMDB
    
    Returns:
        dict: Connection data with host, credentials, protocol, port
    """
    vendor = device["vendor"]
    os_type = device["os_type"]

    capability = resolve_capability(vendor, os_type)

    connection_method = capability["preferred_connection"]
    port = capability["default_port"]

    # Get credentials by vendor from settings
    if vendor not in DEVICE_CREDENTIALS:
        raise Exception(f"No credentials found for vendor: {vendor}")
    
    credentials = DEVICE_CREDENTIALS[vendor]

    connection_data = {
        "host": device["management_host"],
        "vendor": vendor,
        "os_type": os_type,
        "connection_method": connection_method,
        "port": port,
        "username": credentials["username"],
        "password": credentials["password"]
    }

    return connection_data


def connect_nxapi(connection_data):
    """
    Test NX-API connection by executing 'show version'.
    
    Args:
        connection_data: Connection parameters
    
    Returns:
        dict: NX-API response
    """
    url = f"https://{connection_data['host']}:{connection_data['port']}/ins"

    payload = {
        "ins_api": {
            "version": "1.0",
            "type": "cli_show",
            "chunk": "0",
            "sid": "1",
            "input": "show version",
            "output_format": "json"
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        auth=(
            connection_data["username"],
            connection_data["password"]
        ),
        headers=headers,
        json=payload,
        verify=False,
        timeout=30
    )

    return response.json()


def connect_restconf(connection_data):
    
    url = f"https://{connection_data['host']}:{connection_data['port']}/restconf/data"
    
    headers = {
        "Accept": "application/yang-data+json",
        "Content-Type": "application/yang-data+json"
    }
    
    response = requests.get(
        url,
        auth=(
            connection_data["username"],
            connection_data["password"]
        ),
        headers=headers,
        verify=False,
        timeout=30
    )
    
    return response.json()


def connect_to_device(device):
    connection_data = build_connection(device)

    method = connection_data["connection_method"]

    if method == "nxapi_rest":
        return connect_nxapi(connection_data)
    
    elif method == "restconf":
        return connect_restconf(connection_data)

    else:
        raise Exception(f"Unsupported connection method: {method}")
