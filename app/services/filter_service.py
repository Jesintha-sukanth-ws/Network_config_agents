# Handles logic for filtering tasks based on assignment group
def is_network_task(payload: dict) -> bool:
    return payload.get("assignment_group") == "Network Queue"