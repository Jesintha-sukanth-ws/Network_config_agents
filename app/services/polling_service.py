import requests
import time
from config.settings import SERVICENOW_INSTANCE, USERNAME, PASSWORD, NETWORK_GROUP_ID
from app.services.orchestrator_service import process_task

processed_tasks = set()


def update_task_state(task_sys_id: str, state: str):
    """Update task state in ServiceNow"""
    try:
        url = f"{SERVICENOW_INSTANCE}/api/now/table/sc_task/{task_sys_id}"
        state_map = {
            "pending": "-5",
            "open": "1",
            "work_in_progress": "2",
            "closed_complete": "3",
            "closed_incomplete": "4",
            "closed_skipped": "7"
        }
        
        payload = {"state": state_map.get(state, "2")}
        
        response = requests.patch(
            url,
            auth=(USERNAME, PASSWORD),
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f" Task state updated to: {state}")
            return True
        else:
            print(f" Failed to update task state: {response.status_code}")
            return False
            
    except Exception as e:
        print(f" Error updating task state: {e}")
        return False


def poll_servicenow():
    print("Polling started...")

    url = f"{SERVICENOW_INSTANCE}/api/now/table/sc_task"

    params = {
        "sysparm_query": f"assignment_group={NETWORK_GROUP_ID}^state=1",  
        "sysparm_fields": "sys_id,number,short_description,description,cmdb_ci,assignment_group,state,sys_created_on",
        "sysparm_limit": "10",
        "sysparm_order_by": "sys_created_on" 
    }

    while True:
        try:
            response = requests.get(
                url,
                auth=(USERNAME, PASSWORD),
                params=params
            )

            data = response.json()

            print("\n Checking tasks...")

            for task in data.get("result", []):

                task_number = task.get("number")
                task_sys_id = task.get("sys_id")

                if task_number in processed_tasks:
                    continue

                print(f"\n Network Task Found: {task_number}")

                update_task_state(task_sys_id, "work_in_progress")

                
                process_task(task)
                
                processed_tasks.add(task_number)

        except Exception as e:
            print(f" Error: {e}")

        time.sleep(10)