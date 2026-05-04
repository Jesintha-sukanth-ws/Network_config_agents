# Handles CMDB lookup logic using ServiceNow API
import requests
from config.settings import SERVICENOW_INSTANCE, USERNAME, PASSWORD


def get_cmdb_data(ci_name: str):
    try:
        #  STEP 1 — Fetch CI data from cmdb_ci_comm
        url = f"https://dev183581.service-now.com/api/now/table/cmdb_ci_comm"

        params = {
            "name": ci_name,
            "sysparm_fields": "name,model_number,ip_address,u_os_type,u_os_version,manufacturer"
        }

        response = requests.get(
            url,
            auth=(USERNAME, PASSWORD),
            params=params
        )

        response.raise_for_status()
        data = response.json()

        if not data["result"]:
            return {"error": "CI not found"}

        device = data["result"][0]

        #  STEP 2 — Extract manufacturer sys_id
        manufacturer_sys_id = None
        if device.get("manufacturer"):
            manufacturer_sys_id = device["manufacturer"].get("value")

        #  STEP 3 — Resolve vendor name
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

        #  STEP 4 — Build clean output
        return {
            "name": device.get("name"),
            "vendor": vendor_name,
            "model": device.get("model_number"),
            "ip": device.get("ip_address"),
            "os_type": device.get("u_os_type"),
            "os_version": device.get("u_os_version")
        }

    except Exception as e:
        return {"error": str(e)}