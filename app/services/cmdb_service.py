
import requests
from config.settings import SERVICENOW_INSTANCE, USERNAME, PASSWORD


def get_cmdb_data(ci_sys_id: str):
   
    
    try:
        # =====================================================
        # STEP 1: Fetch device metadata from CMDB
        # =====================================================
        url = f"{SERVICENOW_INSTANCE}/api/now/table/cmdb_ci_comm/{ci_sys_id}"

        # Request only the 6 required metadata fields
        # Note: fqdn is preferred over ip_address for management_host
        params = {
            "sysparm_fields": "name,model_number,ip_address,fqdn,u_os_type,u_os_version,manufacturer"
        }

        response = requests.get(
            url,
            auth=(USERNAME, PASSWORD),
            params=params
        )

        response.raise_for_status()
        data = response.json()

        device = data.get("result")
        
        if not device:
            return {"error": "CI not found in CMDB"}

        # =====================================================
        # STEP 2: Extract manufacturer sys_id
        # =====================================================
        manufacturer_sys_id = None
        if device.get("manufacturer"):
            manufacturer_sys_id = device["manufacturer"].get("value")

        # =====================================================
        # STEP 3: Resolve vendor name from manufacturer
        # =====================================================
        vendor_name = "Unknown"

        if manufacturer_sys_id:
            vendor_url = f"{SERVICENOW_INSTANCE}/api/now/table/core_company/{manufacturer_sys_id}"
            vendor_response = requests.get(
                vendor_url,
                auth=(USERNAME, PASSWORD)
            )

            if vendor_response.status_code == 200:
                vendor_data = vendor_response.json()
                vendor_name = vendor_data["result"].get("name", "Unknown")

       
        
        # Prefer FQDN over IP address for management_host
        management_host = device.get("fqdn") or device.get("ip_address")
        
        if not management_host:
            return {"error": "No management host (FQDN or IP) found in CMDB"}
        
        return {
            "device_name": device.get("name"),           # Human-readable identifier
            "vendor": vendor_name,                       # Device vendor
            "model": device.get("model_number"),         # Device model
            "os_type": device.get("u_os_type"),          # OS family (IOS-XE, NX-OS, etc.)
            "os_version": device.get("u_os_version"),    # OS version
            "management_host": management_host           # Management endpoint (FQDN preferred, IP fallback)
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"CMDB connection failed: {str(e)}"}
    except Exception as e:
        return {"error": f"CMDB lookup failed: {str(e)}"}