# =========================================================
# Device State Service
# =========================================================
# PURPOSE:
# Retrieve operational device state using structured API calls.
# Normalize vendor-specific responses into common JSON format.
#
# ARCHITECTURAL PRINCIPLE:
# - Use API-based structured payload retrieval ONLY
# - NO CLI parsing or text scraping
# - Vendor-agnostic normalized output
# - Scalable for multi-vendor support
#
# SUPPORTED VENDORS:
# - Cisco NX-OS (NX-API)
# - Cisco IOS-XE (RESTCONF)
# - Future: Juniper, Palo Alto, Fortinet
# =========================================================

import requests
import json
from typing import Dict, List
from devices.connection_service import build_connection


# =========================================================
# NORMALIZED DATA STRUCTURES
# =========================================================

def normalize_vlans(vendor_response: dict, vendor: str, os_type: str) -> dict:
    """
    Normalize VLAN data from vendor-specific format to common structure.
    
    Returns:
        {
            "vlans": [
                {
                    "vlan_id": int,
                    "name": str,
                    "state": str  # "active", "suspended", etc.
                }
            ]
        }
    """
    if vendor == "Cisco" and os_type == "NX-OS":
        return _normalize_nxos_vlans(vendor_response)
    elif vendor == "Cisco" and os_type == "IOS-XE":
        return _normalize_iosxe_vlans(vendor_response)
    else:
        return {"vlans": [], "error": f"Unsupported vendor/OS: {vendor}/{os_type}"}


def normalize_interfaces(vendor_response: dict, vendor: str, os_type: str) -> dict:
    """
    Normalize interface data from vendor-specific format to common structure.
    
    Returns:
        {
            "interfaces": [
                {
                    "name": str,
                    "status": str,  # "up", "down"
                    "mode": str,    # "access", "trunk", "routed"
                    "access_vlan": int or null,
                    "description": str
                }
            ]
        }
    """
    if vendor == "Cisco" and os_type == "NX-OS":
        return _normalize_nxos_interfaces(vendor_response)
    elif vendor == "Cisco" and os_type == "IOS-XE":
        return _normalize_iosxe_interfaces(vendor_response)
    else:
        return {"interfaces": [], "error": f"Unsupported vendor/OS: {vendor}/{os_type}"}


def normalize_trunks(vendor_response: dict, vendor: str, os_type: str) -> dict:
    """
    Normalize trunk data from vendor-specific format to common structure.
    
    Returns:
        {
            "trunks": [
                {
                    "interface": str,
                    "allowed_vlans": [int],
                    "native_vlan": int or null
                }
            ]
        }
    """
    if vendor == "Cisco" and os_type == "NX-OS":
        return _normalize_nxos_trunks(vendor_response)
    elif vendor == "Cisco" and os_type == "IOS-XE":
        return _normalize_iosxe_trunks(vendor_response)
    else:
        return {"trunks": [], "error": f"Unsupported vendor/OS: {vendor}/{os_type}"}


# =========================================================
# CISCO NX-OS NORMALIZATION (NX-API)
# =========================================================

def _normalize_nxos_vlans(response: dict) -> dict:
    """Normalize Cisco NX-OS VLAN response from NX-API."""
    vlans = []
    
    try:
        # NX-API response structure: ins_api -> outputs -> output -> body -> TABLE_vlanbrief -> ROW_vlanbrief
        body = response.get("ins_api", {}).get("outputs", {}).get("output", {}).get("body", {})
        vlan_table = body.get("TABLE_vlanbrief", {}).get("ROW_vlanbrief", [])
        
        # Handle single VLAN (not in list)
        if isinstance(vlan_table, dict):
            vlan_table = [vlan_table]
        
        for vlan in vlan_table:
            vlans.append({
                "vlan_id": int(vlan.get("vlanshowbr-vlanid-utf", 0)),
                "name": vlan.get("vlanshowbr-vlanname", ""),
                "state": vlan.get("vlanshowbr-vlanstate", "").lower()
            })
    
    except Exception as e:
        return {"vlans": [], "error": f"Failed to parse NX-OS VLANs: {str(e)}"}
    
    return {"vlans": vlans}


def _normalize_nxos_interfaces(response: dict) -> dict:
    """Normalize Cisco NX-OS interface response from NX-API."""
    interfaces = []
    
    try:
        body = response.get("ins_api", {}).get("outputs", {}).get("output", {}).get("body", {})
        intf_table = body.get("TABLE_interface", {}).get("ROW_interface", [])
        
        if isinstance(intf_table, dict):
            intf_table = [intf_table]
        
        for intf in intf_table:
            interfaces.append({
                "name": intf.get("interface", ""),
                "status": intf.get("state", "").lower(),
                "mode": intf.get("mode", "").lower(),
                "access_vlan": int(intf.get("access_vlan", 0)) if intf.get("access_vlan") else None,
                "description": intf.get("desc", "")
            })
    
    except Exception as e:
        return {"interfaces": [], "error": f"Failed to parse NX-OS interfaces: {str(e)}"}
    
    return {"interfaces": interfaces}


def _normalize_nxos_trunks(response: dict) -> dict:
    """Normalize Cisco NX-OS trunk response from NX-API."""
    trunks = []
    
    try:
        body = response.get("ins_api", {}).get("outputs", {}).get("output", {}).get("body", {})
        trunk_table = body.get("TABLE_interface", {}).get("ROW_interface", [])
        
        if isinstance(trunk_table, dict):
            trunk_table = [trunk_table]
        
        for trunk in trunk_table:
            if trunk.get("mode", "").lower() == "trunk":
                # Parse allowed VLANs (format: "1-10,20,30-40")
                allowed_vlans_str = trunk.get("trunkvlans", "")
                allowed_vlans = _parse_vlan_list(allowed_vlans_str)
                
                trunks.append({
                    "interface": trunk.get("interface", ""),
                    "allowed_vlans": allowed_vlans,
                    "native_vlan": int(trunk.get("native_vlan", 1))
                })
    
    except Exception as e:
        return {"trunks": [], "error": f"Failed to parse NX-OS trunks: {str(e)}"}
    
    return {"trunks": trunks}


# =========================================================
# CISCO IOS-XE NORMALIZATION (RESTCONF)
# =========================================================

def _normalize_iosxe_vlans(response: dict) -> dict:
    """Normalize Cisco IOS-XE VLAN response from RESTCONF."""
    vlans = []
    
    try:
        # RESTCONF response structure varies by endpoint
        # Example: /data/Cisco-IOS-XE-vlan-oper:vlans/vlan
        vlan_list = response.get("Cisco-IOS-XE-vlan-oper:vlan", [])
        
        for vlan in vlan_list:
            vlans.append({
                "vlan_id": int(vlan.get("id", 0)),
                "name": vlan.get("name", ""),
                "state": vlan.get("status", "").lower()
            })
    
    except Exception as e:
        return {"vlans": [], "error": f"Failed to parse IOS-XE VLANs: {str(e)}"}
    
    return {"vlans": vlans}


def _normalize_iosxe_interfaces(response: dict) -> dict:
    """Normalize Cisco IOS-XE interface response from RESTCONF."""
    interfaces = []
    
    try:
        # Handle both response structures
        if "ietf-interfaces:interfaces" in response:
            intf_list = response.get("ietf-interfaces:interfaces", {}).get("interface", [])
        else:
            intf_list = response.get("ietf-interfaces:interface", [])
        
        for intf in intf_list:
            # Get admin status (enabled field)
            admin_status = "up" if intf.get("enabled", False) else "down"
            
            # Get operational status
            oper_status = intf.get("oper-status", "unknown")
            
            # For IOS-XE, we need to check if it's a switchport
            # This data might be in Cisco-specific augmentations
            mode = "routed"  # Default for IOS-XE interfaces
            access_vlan = None
            
            # Check if interface has switchport config
            if "Cisco-IOS-XE-switch:switchport-conf" in intf:
                switchport = intf["Cisco-IOS-XE-switch:switchport-conf"]
                mode = switchport.get("mode", "access")
                if mode == "access":
                    access_vlan = switchport.get("access", {}).get("vlan", {}).get("vlan", None)
            
            interfaces.append({
                "name": intf.get("name", ""),
                "status": oper_status if oper_status != "unknown" else admin_status,
                "mode": mode,
                "access_vlan": access_vlan,
                "description": intf.get("description", "")
            })
    
    except Exception as e:
        return {"interfaces": [], "error": f"Failed to parse IOS-XE interfaces: {str(e)}"}
    
    return {"interfaces": interfaces}


def _normalize_iosxe_trunks(response: dict) -> dict:
    """Normalize Cisco IOS-XE trunk response from RESTCONF."""
    trunks = []
    
    try:
        # Handle both response structures
        if "ietf-interfaces:interfaces" in response:
            intf_list = response.get("ietf-interfaces:interfaces", {}).get("interface", [])
        else:
            intf_list = response.get("ietf-interfaces:interface", [])
        
        for intf in intf_list:
            # Check if interface has switchport trunk config
            if "Cisco-IOS-XE-switch:switchport-conf" in intf:
                switchport = intf["Cisco-IOS-XE-switch:switchport-conf"]
                mode = switchport.get("mode", "")
                
                if mode == "trunk":
                    trunk_config = switchport.get("trunk", {})
                    allowed_vlans_str = trunk_config.get("allowed", {}).get("vlan", {}).get("vlans", "")
                    allowed_vlans = _parse_vlan_list(allowed_vlans_str)
                    native_vlan = trunk_config.get("native", {}).get("vlan", {}).get("vlan-id", 1)
                    
                    trunks.append({
                        "interface": intf.get("name", ""),
                        "allowed_vlans": allowed_vlans,
                        "native_vlan": native_vlan
                    })
    
    except Exception as e:
        return {"trunks": [], "error": f"Failed to parse IOS-XE trunks: {str(e)}"}
    
    return {"trunks": trunks}


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def _parse_vlan_list(vlan_str: str) -> List[int]:
    """
    Parse VLAN list string into list of integers.
    
    Examples:
        "1-10,20,30-40" -> [1,2,3,4,5,6,7,8,9,10,20,30,31,32,33,34,35,36,37,38,39,40]
        "10,20,30" -> [10,20,30]
    """
    vlans = []
    
    if not vlan_str:
        return vlans
    
    try:
        for part in vlan_str.split(","):
            if "-" in part:
                start, end = part.split("-")
                vlans.extend(range(int(start), int(end) + 1))
            else:
                vlans.append(int(part))
    except:
        pass
    
    return sorted(list(set(vlans)))


# =========================================================
# API CALL FUNCTIONS
# =========================================================

def _nxapi_call(connection_data: dict, command: str) -> dict:
    """Execute NX-API call and return structured response."""
    url = f"https://{connection_data['host']}:{connection_data['port']}/ins"
    
    payload = {
        "ins_api": {
            "version": "1.0",
            "type": "cli_show",
            "chunk": "0",
            "sid": "1",
            "input": command,
            "output_format": "json"
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(
            url,
            auth=(connection_data["username"], connection_data["password"]),
            headers=headers,
            json=payload,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        
        # DEBUG: Print raw response
        raw_response = response.json()
        print(f"\n[DEBUG] NX-API Command: {command}")
        print(f"[DEBUG] Raw Response: {json.dumps(raw_response, indent=2)}")
        
        return raw_response
    except Exception as e:
        print(f"[DEBUG] NX-API Error for command '{command}': {str(e)}")
        return {"error": str(e)}


def _restconf_call(connection_data: dict, endpoint: str) -> dict:
    """Execute RESTCONF call and return structured response."""
    url = f"https://{connection_data['host']}:{connection_data['port']}/restconf/data/{endpoint}"
    
    headers = {
        "Accept": "application/yang-data+json",
        "Content-Type": "application/yang-data+json"
    }
    
    try:
        response = requests.get(
            url,
            auth=(connection_data["username"], connection_data["password"]),
            headers=headers,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


# =========================================================
# MAIN DEVICE STATE RETRIEVAL FUNCTION
# =========================================================

def get_device_facts(device: dict) -> dict:
    """
    Retrieve operational device state using API calls.
    
    Args:
        device: Device metadata from CMDB with fields:
            - device_name
            - vendor
            - model
            - os_type
            - os_version (may be empty, will be retrieved)
            - management_host
    
    Returns:
        {
            "device_info": {
                "os_version": str,
                "hostname": str
            },
            "vlans": [...],
            "interfaces": [...],
            "trunks": [...]
        }
    """
    vendor = device.get("vendor")
    os_type = device.get("os_type")
    
    # Build connection data
    try:
        connection_data = build_connection(device)
    except Exception as e:
        return {"error": f"Failed to build connection: {str(e)}"}
    
    facts = {
        "device_info": {},
        "vlans": [],
        "interfaces": [],
        "trunks": []
    }
    
    # =====================================================
    # CISCO NX-OS
    # =====================================================
    if vendor == "Cisco" and os_type == "NX-OS":
        
        version_response = _nxapi_call(connection_data, "show version")
        if "error" not in version_response:
            try:
                body = version_response.get("ins_api", {}).get("outputs", {}).get("output", {}).get("body", {})
                facts["device_info"]["os_version"] = body.get("nxos_ver_str", "")
                facts["device_info"]["hostname"] = body.get("host_name", "")
            except:
                pass
        
        # Get VLANs
        vlan_response = _nxapi_call(connection_data, "show vlan brief")
        if "error" not in vlan_response:
            facts.update(normalize_vlans(vlan_response, vendor, os_type))
        
        # Get interfaces
        intf_response = _nxapi_call(connection_data, "show interface switchport")
        if "error" not in intf_response:
            facts.update(normalize_interfaces(intf_response, vendor, os_type))
        
        # Get trunks (same response as interfaces for NX-OS)
        if "error" not in intf_response:
            facts.update(normalize_trunks(intf_response, vendor, os_type))
    
    # =====================================================
    # CISCO IOS-XE
    # =====================================================
    elif vendor == "Cisco" and os_type == "IOS-XE":
        # Get OS version
        version_response = _restconf_call(connection_data, "Cisco-IOS-XE-native:native/version")
        if "error" not in version_response:
            try:
                facts["device_info"]["os_version"] = version_response.get("Cisco-IOS-XE-native:version", "")
            except:
                pass
        
        # Get VLANs
        vlan_response = _restconf_call(connection_data, "Cisco-IOS-XE-vlan-oper:vlans")
        if "error" not in vlan_response:
            facts.update(normalize_vlans(vlan_response, vendor, os_type))
        
        # Get interfaces
        intf_response = _restconf_call(connection_data, "ietf-interfaces:interfaces")
        if "error" not in intf_response:
            facts.update(normalize_interfaces(intf_response, vendor, os_type))
            facts.update(normalize_trunks(intf_response, vendor, os_type))
    
    else:
        return {"error": f"Unsupported vendor/OS: {vendor}/{os_type}"}
    
    return facts
