import time
import threading
import logging
import requests
from requests.auth import HTTPBasicAuth

from config.settings import (
    SERVICENOW_INSTANCE,
    SERVICENOW_USERNAME,
    SERVICENOW_PASSWORD,
    NETWORK_GROUP_ID,
    SERVICENOW_SSL_VERIFY,
    SERVICENOW_TIMEOUT,
    POLL_INTERVAL,
)

from app.services.orchestrator_service import process_task

# ----------------------------------------
# Logging
# ----------------------------------------

logger = logging.getLogger(__name__)


# ----------------------------------------
# ServiceNow Task States
# ----------------------------------------

TASK_STATES = {
    "OPEN": "1",
    "WORK_IN_PROGRESS": "2",
    "CLOSED_COMPLETE": "3",
    "CLOSED_INCOMPLETE": "4",
}


# ----------------------------------------
# Fetch next task
# ----------------------------------------

def get_next_open_task():

    url = (
        f"{SERVICENOW_INSTANCE}"
        "/api/now/table/sc_task"
    )

    params = {
        "sysparm_query": (
            f"assignment_group={NETWORK_GROUP_ID}"
            "^state=1"
            "^approval=approved"
        ),
        "sysparm_limit": "1",
        "sysparm_fields": (
            "sys_id,"
            "number,"
            "short_description,"
            "description,"
            "variables,"
            "cmdb_ci"
        ),
    }

    try:
        auth = HTTPBasicAuth(
            str(SERVICENOW_USERNAME or ""),
            str(SERVICENOW_PASSWORD or ""),
        )
        timeout_value = None
        if SERVICENOW_TIMEOUT is not None:
            try:
                timeout_value = float(SERVICENOW_TIMEOUT)
            except (TypeError, ValueError):
                timeout_value = None

        response = requests.get(
            url,
            auth=auth,
            params=params,
            verify=SERVICENOW_SSL_VERIFY,
            timeout=timeout_value,
        )
        response.raise_for_status()

        tasks = response.json().get("result", [])
        return tasks[0] if tasks else None

    except requests.RequestException as e:
        logger.error("ServiceNow fetch error: %s", e)
        return None


# ----------------------------------------
# Update task state
# ----------------------------------------

def update_task_state(task_sys_id: str, state: str) -> bool:

    url = (
        f"{SERVICENOW_INSTANCE}"
        f"/api/now/table/sc_task/{task_sys_id}"
    )

    payload = {"state": state}

    try:
        auth = HTTPBasicAuth(
            str(SERVICENOW_USERNAME or ""),
            str(SERVICENOW_PASSWORD or ""),
        )
        timeout_value = None
        if SERVICENOW_TIMEOUT is not None:
            try:
                timeout_value = float(SERVICENOW_TIMEOUT)
            except (TypeError, ValueError):
                timeout_value = None

        response = requests.patch(
            url,
            auth=auth,
            json=payload,
            verify=SERVICENOW_SSL_VERIFY,
            timeout=timeout_value,
        )
        response.raise_for_status()
        return True

    except requests.RequestException as e:
        logger.error("Failed updating task state: %s", e)
        return False


# ----------------------------------------
# Update task work notes
# ----------------------------------------

def update_task_work_notes(task_sys_id: str, work_notes: str) -> bool:

    url = (
        f"{SERVICENOW_INSTANCE}"
        f"/api/now/table/sc_task/{task_sys_id}"
    )

    payload = {"work_notes": work_notes}

    try:
        logger.info(
            "Updating work notes for sc_task (%s)",
            task_sys_id,
        )
        auth = HTTPBasicAuth(
            str(SERVICENOW_USERNAME or ""),
            str(SERVICENOW_PASSWORD or ""),
        )
        timeout_value = None
        if SERVICENOW_TIMEOUT is not None:
            try:
                timeout_value = float(SERVICENOW_TIMEOUT)
            except (TypeError, ValueError):
                timeout_value = None

        response = requests.patch(
            url,
            auth=auth,
            json=payload,
            verify=SERVICENOW_SSL_VERIFY,
            timeout=timeout_value,
        )
        if response.status_code == 200:
            logger.info(
                "Work notes updated successfully for sc_task (%s)",
                task_sys_id,
            )
            return True

        logger.error(
            "Work note update failed. status=%s response=%s",
            response.status_code,
            response.text,
        )
        return False

    except requests.RequestException as e:
        logger.exception("Exception occurred while updating work notes")
        return False


# ----------------------------------------
# Poller Loop
# ----------------------------------------

def poll_servicenow(stop_event: threading.Event | None = None):
    """
    Long-running ServiceNow poller.
    
    Polls ServiceNow for approved tasks and processes them using the
    CR Lifecycle Agent framework. Safely falls back to legacy synchronous 
    orchestration if the lifecycle agent configuration is unavailable.
    
    Args:
        stop_event: Optional threading.Event to signal shutdown
    """

    logger.info("ServiceNow poller started")

    # Safe dynamic lookup of the lifecycle component to preserve backward compatibility
    try:
        from app.services.cr_lifecycle_agent import CRLifecycleAgent
        lifecycle_agent = CRLifecycleAgent()
        logger.info("Asynchronous Change Management lifecycle tracking enabled.")
    except (ImportError, ModuleNotFoundError, Exception) as err:
        lifecycle_agent = None
        logger.warning(
            "CRLifecycleAgent could not be loaded; falling back to legacy synchronous execution loop. Exception: %s", 
            err
        )

    # Initialize narrative service
    try:
        from app.services.itsm_narrative_service import (
            ITSMNarrativeService,
            NarrativeType,
        )
        narrative_service = ITSMNarrativeService()
    except Exception as e:
        narrative_service = None
        logger.warning("ITSMNarrativeService could not be initialized: %s", e)

    while True:

        if stop_event is not None and stop_event.is_set():
            logger.info("Polling stop requested; exiting loop")
            return

        work_done = False

        try:
            # ── PASS 1: Reconcile Outstanding, Long-running Approved Changes ────
            if lifecycle_agent is not None:
                try:
                    # Check active states tracked inside cr_tracking.json and drive executions
                    lifecycle_agent.reconcile_active_changes()
                except Exception as lifecycle_err:
                    logger.exception("Error during lifecycle tracking reconciliation: %s", lifecycle_err)

            # ── PASS 2: Ingest Brand New Incoming Request Contexts ──────────────
            task = get_next_open_task()

            if not task:
                logger.debug("No approved tasks found")
                if not work_done:
                    _wait(stop_event, int(POLL_INTERVAL) if POLL_INTERVAL is not None else 60)
                continue

            
            task_id = task.get("sys_id")
            task_number = task.get("number")

            # Defensive Check: Ensure this target isn't already caught in the change loop
            if (
                lifecycle_agent is not None
                and lifecycle_agent.is_tracked(task_number)
            ):
                logger.debug(
                    "Task %s is already explicitly tracked under a lifecycle workflow.",
                    task_number,
                )
                continue

            acquired = update_task_state(
                task_id,
                TASK_STATES["WORK_IN_PROGRESS"],
            )

            if not acquired:
                logger.warning("Unable to acquire %s", task_number)
                continue

            logger.info("Processing %s", task_number)
            work_done = True

            # ── PASS 3: Route Execution Flow Based on System Topology Mode ──────
            if lifecycle_agent is not None:
                try:
                    # Route task through the CR lifecycle engine
                    result = lifecycle_agent.initialize_lifecycle(task)

                    if isinstance(result, dict) and result.get("status") == "failed":
                        logger.warning("%s lifecycle execution failed: %s", task_number, result)
                        
                        # Generate audit trail for failure
                        if narrative_service is not None:
                            try:
                                notes = narrative_service.generate_task_work_notes(
                                    narrative_type=NarrativeType.TASK_FAILURE,
                                    task_number=task_number,
                                    short_description=task.get("short_description", ""),
                                    description=task.get("description", ""),
                                    technical_details=result.get(
                                        "error",
                                        "Lifecycle initialization failed.",
                                    ),
                                )
                                logger.info(
                                    "Diagnostic: updating work notes for %s with generated content: %s",
                                    task_number,
                                    notes,
                                )
                                update_task_work_notes(task_id, notes)
                            except Exception as n_err:
                                logger.error(
                                    "Failed to generate/update failure narrative for %s: %s",
                                    task_number,
                                    n_err,
                                )

                        update_task_state(
                            task_id,
                            TASK_STATES["CLOSED_INCOMPLETE"],
                        )

                except Exception as e:
                    logger.exception(
                        "Failed to process lifecycle workflow for %s",
                        task_number,
                    )
                    
                    if narrative_service is not None:
                        try:
                            notes = narrative_service.generate_task_work_notes(
                                narrative_type=NarrativeType.TASK_FAILURE,
                                task_number=task_number,
                                short_description=task.get("short_description", ""),
                                description=task.get("description", ""),
                                technical_details=str(e),
                            )
                            logger.info(
                                "Diagnostic: updating work notes for %s with generated content: %s",
                                task_number,
                                notes,
                            )
                            update_task_work_notes(task_id, notes)
                        except Exception as n_err:
                            logger.error("Failed to generate/update failure narrative for %s: %s", task_number, n_err)

                    update_task_state(
                        task_id,
                        TASK_STATES["CLOSED_INCOMPLETE"],
                    )
            else:
                # Legacy Backward Compatibility Fallback Code path
                try:
                    result = process_task(task)
                    status = result.get("status")

                    final_state = (
                        TASK_STATES["CLOSED_COMPLETE"]
                        if status == "success"
                        else TASK_STATES["CLOSED_INCOMPLETE"]
                    )

                    update_task_state(task_id, final_state)
                    logger.info("%s completed synchronously with status=%s", task_number, status)

                except Exception as e:
                    logger.exception(
                        "Synchronous legacy execution failed for %s: %s",
                        task_number,
                        e,
                    )
                    update_task_state(
                        task_id,
                        TASK_STATES["CLOSED_INCOMPLETE"],
                    )

        except Exception as e:
            logger.exception("Poller error: %s", e)
            if not work_done:
                _wait(stop_event, POLL_INTERVAL)


def _wait(stop_event, seconds: int | None):
    """Sleep that respects an optional stop_event."""
    if stop_event is None:
        if seconds is not None:
            time.sleep(seconds)
        return
    if seconds is not None:
        stop_event.wait(timeout=seconds)