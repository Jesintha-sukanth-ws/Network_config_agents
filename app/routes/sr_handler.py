from fastapi import APIRouter
from app.services.filter_service import is_network_task
from app.services.cmdb_service import get_cmdb_data

router = APIRouter()

@router.post("/sr-handler")
async def receive_task(payload: dict):
    print("\n Incoming Request ")
    print(payload)
    print("--------------------\n")

    # Step 1 — Filter
    if not is_network_task(payload):
        print(" Ignored: Not a Network Queue task\n")
        return {
            "status": "ignored",
            "reason": "Not a Network Queue task"
        }

    print(" Valid Network Task — Processing...\n")

    #  Step 2 — Extract CI name
    ci_name = payload.get("configuration_item", {}).get("name")

    print(f" Looking up CMDB for: {ci_name}")

    #  Step 3 — Call CMDB
    device_details = get_cmdb_data(ci_name)

    print("\n Device Details from CMDB:")
    print(device_details)
    print("\n--------------------\n")

    # 🔹 Step 4 — Return enriched response
    return {
        "status": "processed",
        "device": device_details
    }