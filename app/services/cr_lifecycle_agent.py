from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

import requests

from config.settings import (
    SERVICENOW_INSTANCE,
    SERVICENOW_USERNAME,
    SERVICENOW_PASSWORD,
    NETWORK_GROUP_ID,
    SERVICENOW_SSL_VERIFY,
    SERVICENOW_TIMEOUT,
)

logger = logging.getLogger(__name__)

class CRLifecycleAgent:
    def __init__(self, tracking_file: str = "data/tracking/cr_tracking.json"):
        self.tracking_file = tracking_file
        self.tracking_data = self._load_tracking()
        
        # Initialize Narrative Service safely
        self.narrative_service = None
        self.NarrativeType = None
        try:
            from app.services.itsm_narrative_service import ITSMNarrativeService, NarrativeType
            self.narrative_service = ITSMNarrativeService()
            self.NarrativeType = NarrativeType
        except Exception as e:
            logger.error("Failed to initialize ITSMNarrativeService: %s", e)

    def _load_tracking(self) -> Dict[str, Any]:
        """Loads or builds empty tracking payload safely."""
        if not os.path.exists(self.tracking_file):
            os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
            return {"tasks": {}}
        try:
            if os.path.getsize(self.tracking_file) == 0:
                return {"tasks": {}}
            with open(self.tracking_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to parse tracking file, initializing empty structure: %s", e)
            return {"tasks": {}}

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _append_stage_history(
        self,
        task_meta: Dict[str, Any],
        stage: str,
        status: str,
        message: str = "",
    ) -> None:
        if "stage_history" not in task_meta or not isinstance(task_meta["stage_history"], list):
            task_meta["stage_history"] = []
        task_meta["stage_history"].append(
            {
                "timestamp": self._now_iso(),
                "stage": stage,
                "status": status,
                "message": message,
            }
        )

    def _save_tracking(self) -> None:
        """Saves active state transitions locally using an atomic write.

        Uses a custom JSON default so Python sets (produced by
        DeviceStateService._build_lookup_state for VLAN lookups) are
        serialized as sorted lists instead of raising TypeError.
        """
        def _json_default(obj):
            if isinstance(obj, set):
                return sorted(obj)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        tmp_path = self.tracking_file + ".tmp"
        try:
            with open(tmp_path, "w") as f:
                json.dump(self.tracking_data, f, indent=2, default=_json_default)
            os.replace(tmp_path, self.tracking_file)
        except Exception as e:
            logger.error("Failed to write cr_tracking.json cache file: %s", e)
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass

    def _update_work_notes(self, table: str, sys_id: str, notes: str) -> bool:
        """Helper to programmatically patch work notes on the instance."""
        url = f"{SERVICENOW_INSTANCE}/api/now/table/{table}/{sys_id}"
        try:
            logger.info(
                "Updating work notes for %s (%s)",
                table,
                sys_id,
            )
            response = requests.patch(
                url,
                auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json={"work_notes": notes},
                verify=SERVICENOW_SSL_VERIFY,
                timeout=SERVICENOW_TIMEOUT
            )
            if response.status_code == 200:
                logger.info(
                    "Work notes updated successfully for %s (%s)",
                    table,
                    sys_id,
                )
                return True

            logger.error(
                "Work note update failed. status=%s response=%s",
                response.status_code,
                response.text,
            )
            return False
        except Exception as e:
            logger.exception("Exception occurred while updating work notes")
            return False

    def _post_narrative(self, event_type: Any, task_number: str, cr_sys_id: str, cr_number: str, sctask_sys_id: str, short_desc: str = "", desc: str = "", technical_details: str = ""):
        """Generates and posts narrative updates if service is available."""
        if not self.narrative_service or not self.NarrativeType:
            return

        try:
            if event_type in (
                self.NarrativeType.CR_CREATED,
                self.NarrativeType.CR_AWAITING_APPROVAL,
                self.NarrativeType.CR_IMPLEMENTING,
                self.NarrativeType.CR_VERIFYING,
                self.NarrativeType.CR_SUCCESS,
                self.NarrativeType.CR_FAILURE,
            ) and hasattr(self.narrative_service, "generate_cr_work_note"):
                notes = self.narrative_service.generate_cr_work_note(
                    narrative_type=event_type,
                    change_number=cr_number,
                    short_description=short_desc,
                    technical_details=technical_details,
                )
            else:
                notes = self.narrative_service.generate_task_work_notes(
                    narrative_type=event_type,
                    task_number=task_number,
                    short_description=short_desc,
                    description=desc,
                    technical_details=technical_details,
                )

            if not notes:
                logger.warning("Narrative generation returned empty text for %s", task_number)
                return

            # Post to Change Request
            cr_updated = self._update_work_notes("change_request", cr_sys_id, notes)
            # Post to SCTASK
            task_updated = self._update_work_notes("sc_task", sctask_sys_id, notes)
            
            if not cr_updated:
                logger.warning("CR work note update failed for %s", cr_number)
            if not task_updated:
                logger.warning("SCTASK work note update failed for %s", task_number)
                
        except Exception as e:
            logger.error("Failed to generate/update narrative for %s: %s", task_number, e)

    def is_tracked(self, task_number: str) -> bool:
        """
        Returns True if the SCTASK number is already participating in an
        ACTIVE lifecycle workflow.

        Closed entries are excluded so that a genuinely re-opened or
        re-submitted SCTASK can be picked up and processed again.
        """
        tasks = self.tracking_data.get("tasks", {})
        for metadata in tasks.values():
            if metadata.get("task_number") == task_number:
                # Only block re-ingestion for non-terminal stages
                if metadata.get("lifecycle_stage") != "Closed":
                    return True
        return False

    def _update_remote_state(self, change_sys_id: str, target_state: str) -> bool:
        """Helper to programmatically patch change request states on the instance."""
        url = f"{SERVICENOW_INSTANCE}/api/now/table/change_request/{change_sys_id}"
        try:
            response = requests.patch(
                url,
                auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json={"state": target_state},
                verify=SERVICENOW_SSL_VERIFY,
                timeout=SERVICENOW_TIMEOUT
            )
            return response.status_code == 200
        except Exception as e:
            logger.error("Failed patching state %s for Change SysID %s: %s", target_state, change_sys_id, e)
            return False

    def _update_sc_task_state(self, task_sys_id: str, state: str) -> bool:
        """Helper to programmatically patch SC Task states on the instance."""
        url = f"{SERVICENOW_INSTANCE}/api/now/table/sc_task/{task_sys_id}"
        try:
            response = requests.patch(
                url,
                auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json={"state": state},
                verify=SERVICENOW_SSL_VERIFY,
                timeout=SERVICENOW_TIMEOUT
            )
            return response.status_code == 200
        except Exception as e:
            logger.error("Failed patching state %s for SCTASK SysID %s: %s", state, task_sys_id, e)
            return False

    def _generate_llm_justification(self, short_description: str, description: str) -> str:
        """
        Calls the local Ollama instance running 'nemotron-3-ultra' using correct 
        native library interfaces with system prompt guardrails.
        """
        try:
            import ollama  # Using the standard official native client library directly

            system_prompt = (
                "You are an expert ITSM Change Coordinator. Your task is to generate a concise, 1-2 sentence corporate "
                "business justification for an infrastructure change request. Do not include raw config lines, switch "
                "commands, parameters, or markdown formatting. Focus exclusively on operational readiness, onboarding, "
                "or capacity enhancement goals explicitly mentioned in the text."
            )
            
            user_prompt = (
                f"Short Description: {short_description}\n"
                f"Full Description: {description}\n\n"
                "Justification:"
            )

            # Standard native module-level method call
            response = ollama.chat(
                model="nemotron-3-ultra:cloud",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            response_text = response.get("message", {}).get("content", "")
            if response_text and len(response_text.strip()) > 10:
                return response_text.strip()
        except Exception as e:
            logger.error("LLM Justification generation failed; applying safety fallback: %s", e)
            
        return f"Automated infrastructure updates initiated to fulfill requested scope parameters for task: {short_description}."

    def create_change_request(self, task: Dict[str, Any], prepared_ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Builds and posts a Change Request payload directly into the 'Assess' phase."""
        sctask_sys_id = task.get("sys_id")
        sctask_number = task.get("number", "Unknown Task")
        sctask_short_desc = task.get("short_description") or ""
        sctask_desc = task.get("description") or sctask_short_desc or ""
        ordered_workflow = prepared_ctx.get("execution_plan", [])

        impl_plan_lines = ["Automated Infrastructure Deployment Sequence:"]
        for idx, step in enumerate(ordered_workflow, 1):
            impl_plan_lines.append(
                f"  Step {idx}: Action '{step.get('intent_type')}' with parameters: "
                f"{json.dumps(step.get('parameters'))}"
            )
        implementation_plan = "\n".join(impl_plan_lines)

        justification_text = self._generate_llm_justification(sctask_short_desc, sctask_desc)

        payload = {
            "short_description": f"Automated Network Provisioning for {sctask_number}",
            "description": f"Refined from source ticket description:\n\n{sctask_desc}",
            "justification": justification_text,
            "implementation_plan": implementation_plan,
            "assignment_group": NETWORK_GROUP_ID,
            "type": "normal",
            "state": "-4"  # Initialized in 'Assess' stage
        }

        url = f"{SERVICENOW_INSTANCE}/api/now/table/change_request"
        try:
            response = requests.post(
                url,
                auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json=payload,
                verify=SERVICENOW_SSL_VERIFY,
                timeout=SERVICENOW_TIMEOUT
            )
            
            if response.status_code not in (200, 201):
                raise RuntimeError(f"ServiceNow API error status={response.status_code}: {response.text}")

            result_data = response.json().get("result", {})
            chg_sys_id = result_data.get("sys_id")
            chg_number = result_data.get("number")

            logger.info("Created Change Request %s matching %s inside Assess phase", chg_number, sctask_number)
            
            # Post audit narrative
            if self.NarrativeType:
                self._post_narrative(
                    event_type=self.NarrativeType.CR_CREATED,
                    task_number=sctask_number,
                    cr_sys_id=chg_sys_id,
                    cr_number=chg_number,
                    sctask_sys_id=sctask_sys_id,
                    short_desc=sctask_short_desc,
                    desc=sctask_desc,
                    technical_details="Change request created and initialized in Assess phase."
                )

            # Persist execution context fields
            if "tasks" not in self.tracking_data:
                self.tracking_data["tasks"] = {}
            self.tracking_data["tasks"][sctask_sys_id] = {
                "task_number": sctask_number,
                "short_description": sctask_short_desc,
                "description": sctask_desc,
                "change_sys_id": chg_sys_id,
                "change_number": chg_number,
                "lifecycle_stage": "Assess",
                "device_data": prepared_ctx["device_data"],

                "execution_plan": prepared_ctx["execution_plan"],
                "generated_payloads": prepared_ctx["generated_payloads"],
                "verification_plan": prepared_ctx["verification_plan"],
                "stage_history": [
                    {
                        "timestamp": self._now_iso(),
                        "stage": "SCTASK_RECEIVED",
                        "status": "success",
                        "message": "ServiceNow SCTASK ingested into the lifecycle workflow.",
                    },
                    {
                        "timestamp": self._now_iso(),
                        "stage": "CHANGE_REQUEST_CREATED",
                        "status": "success",
                        "message": "Change Request created and initialized in Assess phase.",
                    },
                ],
            }
            self._save_tracking()
            
            return {"status": "success", "change_number": chg_number, "change_sys_id": chg_sys_id}

        except Exception as e:
            logger.exception("Failed to insert Change Request records inside ServiceNow: %s", e)
            return {"status": "failed", "error": str(e)}

    def initialize_lifecycle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Poller call-site entry point to map incoming tasks."""
        from app.services.orchestrator_service import plan_task, prepare_change
        sctask_number = task.get("number", "Unknown")

        try:
            plan_res = plan_task(task)
        except Exception as exc:
            logger.error("plan_task raised unexpectedly for %s: %s", sctask_number, exc)
            return {"status": "failed", "error": f"Planning exception: {exc}"}

        if not plan_res.get("safe", True):
            logger.error("Pre-validation checks failed for %s. Tracking skipped.", sctask_number)
            return {"status": "failed", "error": "Pre-validation failed"}

        try:
            prepared_ctx = prepare_change(plan_res, task_id=sctask_number)
        except Exception as exc:
            logger.error("prepare_change raised unexpectedly for %s: %s", sctask_number, exc)
            return {"status": "failed", "error": f"Preparation exception: {exc}"}

        if not prepared_ctx.get("safe", False):
            error_msg = prepared_ctx.get("message", "Preparation failed")
            is_terminal = prepared_ctx.get("terminal_failure", False)
            logger.error(
                "Preparation failed for %s (terminal=%s): %s",
                sctask_number, is_terminal, error_msg,
            )
            return {"status": "failed", "error": error_msg, "terminal_failure": is_terminal}

        # Handle idempotent case - no implementation needed
        if prepared_ctx.get("idempotent", False):
            return self._handle_idempotent_task(task, prepared_ctx)

        return self.create_change_request(task, prepared_ctx)

    def _handle_idempotent_task(self, task: Dict[str, Any], prepared_ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tasks where no configuration changes are required."""
        sctask_sys_id = task.get("sys_id")
        sctask_number = task.get("number", "Unknown Task")
        sctask_short_desc = task.get("short_description") or ""
        sctask_desc = task.get("description") or sctask_short_desc or ""

        # Create CR but move directly to Review state
        payload = {
            "short_description": f"Idempotent Network Configuration for {sctask_number}",
            "description": f"Pre-change validation determined that the requested configuration already exists on the target device:\n\n{sctask_desc}",
            "justification": "No implementation actions were required as the target configuration already exists on the device.",
            "implementation_plan": "No implementation required - target configuration already exists.",
            "assignment_group": NETWORK_GROUP_ID,
            "type": "normal",
            "state": "0",  # Review state
            "close_code": "successful",
            "close_notes": prepared_ctx.get("message", "Requested configuration already exists on the target device. No changes were required. Implementation was skipped.")
        }

        url = f"{SERVICENOW_INSTANCE}/api/now/table/change_request"
        try:
            response = requests.post(
                url,
                auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json=payload,
                verify=SERVICENOW_SSL_VERIFY,
                timeout=SERVICENOW_TIMEOUT
            )
            
            if response.status_code not in (200, 201):
                raise RuntimeError(f"ServiceNow API error status={response.status_code}: {response.text}")

            result_data = response.json().get("result", {})
            chg_sys_id = result_data.get("sys_id")
            chg_number = result_data.get("number")

            logger.info("Created idempotent Change Request %s for %s in Review state", chg_number, sctask_number)
            
            # Update SCTASK to Closed Incomplete with appropriate work notes
            idempotent_work_note = (
                "Change request created for idempotent operation.\n"
                "Pre-change validation determined that the requested configuration already exists on the target device.\n"
                "No implementation actions were required. Task closed incomplete as no changes were necessary."
            )
            
            if self._update_sc_task_state(sctask_sys_id, "4"):  # Closed Incomplete
                self._update_work_notes("sc_task", sctask_sys_id, idempotent_work_note)
                logger.info("SCTASK %s closed incomplete for idempotent operation", sctask_number)
            else:
                logger.error("Failed to close idempotent SCTASK %s", sctask_number)

            return {"status": "success", "change_number": chg_number, "change_sys_id": chg_sys_id, "idempotent": True}

        except Exception as e:
            logger.exception("Failed to create idempotent Change Request: %s", e)
            return {"status": "failed", "error": str(e)}

    def reconcile_active_changes(self) -> None:
        """
        Monitors milestones sequentially within an explicit, mutually exclusive evaluation architecture.
        Ensures Assess (-4) and Authorize (-3) cleanly wait for manual intervention.
        """
        tasks = self.tracking_data.get("tasks", {})
        if not tasks:
            return

        from app.services.orchestrator_service import implement_change

        for sctask_sys_id, meta in list(tasks.items()):
            current_stage = meta.get("lifecycle_stage")
            if current_stage == "Closed":
                continue

            change_sys_id = meta.get("change_sys_id")
            change_number = meta.get("change_number")
            sctask_number = meta.get("task_number")
            
            url = f"{SERVICENOW_INSTANCE}/api/now/table/change_request/{change_sys_id}"
            try:
                response = requests.get(
                    url,
                    auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
                    headers={"Accept": "application/json"},
                    verify=SERVICENOW_SSL_VERIFY,
                    timeout=SERVICENOW_TIMEOUT
                )
                if response.status_code != 200:
                    continue
                    
                cr_data = response.json().get("result", {})
                live_state = str(cr_data.get("state"))

                # -------------------------------------------------------------
                # MUTUALLY EXCLUSIVE LIFECYCLE EVALUATION ENGINE
                # -------------------------------------------------------------
                if live_state == "-4":
                    if current_stage != "Assess":
                        logger.info("Change Request %s initialized. Waiting in Assess phase.", change_number)
                        meta["lifecycle_stage"] = "Assess"
                        self._save_tracking()

                elif live_state == "-3":
                    if current_stage != "Authorize":
                        logger.info("Change Request %s moved to Authorize phase. Awaiting approvals.", change_number)
                        meta["lifecycle_stage"] = "Authorize"
                        self._append_stage_history(
                            meta,
                            "CHANGE_REQUEST_AWAITING_APPROVAL",
                            "success",
                            "Change request entered authorization stage and is awaiting approval.",
                        )
                        self._save_tracking()

                        if self.NarrativeType:
                            self._post_narrative(
                                event_type=self.NarrativeType.CR_AWAITING_APPROVAL,
                                task_number=sctask_number,
                                cr_sys_id=change_sys_id,
                                cr_number=change_number,
                                sctask_sys_id=sctask_sys_id,
                                technical_details="Change request entered authorization stage. Approval is required before implementation."
                            )

                elif live_state == "-2":
                    if current_stage == "Authorize":
                        self._append_stage_history(
                            meta,
                            "CHANGE_REQUEST_APPROVED",
                            "success",
                            "Change request approval completed and is ready for implementation.",
                        )
                        self._save_tracking()

                    logger.info("[FORCE ACTIVE] Change Request %s reached Scheduled window. Forcing transition to Implement (-1)...", change_number)
                    if self._update_remote_state(change_sys_id, "-1"):
                        # Force local variable update to evaluate and execute immediately on this loop cycle
                        live_state = "-1"
                    else:
                        logger.error("Failed to automatically advance %s to Implement phase", change_number)

                # -------------------------------------------------------------
                # STAGE 4: IMPLEMENT PHASE (-1) -> ONLY RUNS WHEN LIVE_STATE IS -1
                # -------------------------------------------------------------
                if live_state == "-1" and current_stage != "Executing":
                    if current_stage == "Authorize":
                        self._append_stage_history(
                            meta,
                            "CHANGE_REQUEST_APPROVED",
                            "success",
                            "Change request approval completed and implementation has begun.",
                        )
                    logger.info("Change Request %s entered Implement state. Executing configuration push...", change_number)
                    meta["lifecycle_stage"] = "Executing"
                    self._append_stage_history(
                        meta,
                        "CONFIGURATION_EXECUTING",
                        "success",
                        "Approved implementation activities have started.",
                    )
                    self._save_tracking()
                    
                    # Post Implementation Started narrative
                    if self.NarrativeType:
                        self._post_narrative(
                            event_type=self.NarrativeType.CR_IMPLEMENTING,
                            task_number=sctask_number,
                            cr_sys_id=change_sys_id,
                            cr_number=change_number,
                            sctask_sys_id=sctask_sys_id,
                            technical_details="Approved implementation activities have started."
                        )

                    # Reconstruct and execute using approved context from persistence
                    prepared_context = {
                        "task_number": change_number,
                        "device_data": meta["device_data"],

                        "execution_plan": meta["execution_plan"],
                        "generated_payloads": meta["generated_payloads"],
                        "verification_plan": meta["verification_plan"],
                    }
                    execution_result = implement_change(prepared_context)

                    # Persist before/after state for dashboard visualization
                    # before_state = device state captured BEFORE config push (from prepare_change)
                    # after_state  = actual_state from verification AFTER config push
                    before_state = meta.get("device_state", {})
                    after_state = {}
                    for step_result in (execution_result.get("results", []) if isinstance(execution_result, dict) else []):
                        verify_data = step_result.get("verify", {})
                        if verify_data.get("actual_state"):
                            after_state = verify_data["actual_state"]
                            break

                    meta["before_state"] = before_state
                    meta["after_state"] = after_state
                    meta["execution_results"] = execution_result.get("results", []) if isinstance(execution_result, dict) else []
                    self._save_tracking()

                    is_success = False
                    close_notes_msg = ""

                    if isinstance(execution_result, dict):
                        is_success = (execution_result.get("status") == "success")
                        steps = execution_result.get("results", [])
                        
                        if steps:
                            failed_steps = [s for s in steps if s.get("status") == "failed"]
                            idempotent_exceptions = ["already enabled", "already exists", "vlan already configured", "no change required"]
                            
                            if failed_steps:
                                all_failures_are_idempotent = True
                                for f_step in failed_steps:
                                    err_msg = str(f_step.get("error", "")).lower()
                                    if not any(msg in err_msg for msg in idempotent_exceptions):
                                        all_failures_are_idempotent = False
                                        break
                                
                                if all_failures_are_idempotent:
                                    is_success = True
                                    close_notes_msg = "Automated execution completed. Target environment was already matching requirements."

                    target_state = "0"
                    terminal_label = "Review"

                    patch_payload = {"state": target_state}
                    if not is_success:
                        patch_payload["close_notes"] = "Automated post-change execution validation failed critically. Routed to Review state."

                    # Extract actual system outcomes context without exposing internal stack/payload structures
                    steps_list = execution_result.get("results", []) if isinstance(execution_result, dict) else []
                    total_steps = len(steps_list)
                    
                    if is_success:
                        tech_details = (
                            f"Automated execution completed successfully. Total executed steps: {total_steps}. "
                            f"Verification outcome: All steps verified and confirmed baseline status. Overall status: success."
                        )
                        if close_notes_msg:
                            tech_details += f" Context: {close_notes_msg}"
                    else:
                        failed_ops = [str(s.get("operation", "unknown")) for s in steps_list if s.get("status") in ("failed", "aborted")]
                        tech_details = (
                            f"Automated execution or verification failed. Total executed steps: {total_steps}. "
                            f"Failed operations: {', '.join(failed_ops) if failed_ops else 'execution error'}. "
                            f"Verification outcome: Critical post-change verification failures detected. Overall status: failed. Review required."
                        )

                    # AI Generated Close Notes Integration
                    close_notes_payload = close_notes_msg or "Automated configuration push completed successfully."
                    if self.narrative_service and hasattr(self.narrative_service, "generate_cr_close_notes") and self.NarrativeType:
                        try:
                            ai_close_notes = self.narrative_service.generate_cr_close_notes(
                                narrative_type=self.NarrativeType.CR_SUCCESS if is_success else self.NarrativeType.CR_FAILURE,
                                change_number=change_number,
                                short_description=meta.get("short_description", ""),
                                execution_summary=tech_details
                            )
                            if ai_close_notes:
                                close_notes_payload = ai_close_notes
                        except Exception as e:
                            logger.exception("Failed to generate AI close notes narrative: %s", e)

                    if is_success:
                        meta["auto_close_ready"] = True
                        meta["close_notes_payload"] = close_notes_payload
                    else:
                        meta["auto_close_ready"] = False

                    patch_response = requests.patch(
                        url,
                        auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
                        headers={"Content-Type": "application/json", "Accept": "application/json"},
                        json=patch_payload,
                        verify=SERVICENOW_SSL_VERIFY,
                        timeout=SERVICENOW_TIMEOUT
                    )

                    # FIX 2: Moved narrative updates inside response validation scope to guard against false success/failure reports
                    if patch_response.status_code == 200:
                        logger.info("Change Request %s successfully transitioned to: %s", change_number, terminal_label)
                        meta["lifecycle_stage"] = terminal_label
                        self._append_stage_history(
                            meta,
                            "CONFIGURATION_VERIFIED",
                            "success" if is_success else "failed",
                            "Automated configuration execution completed and verification was recorded.",
                        )
                        
                        # Update SCTASK state immediately after execution completes (success or partial failure)
                        if is_success:
                            # Execution succeeded - close SCTASK as complete
                            if self._update_sc_task_state(sctask_sys_id, "3"):
                                success_work_note = (
                                    "Change request executed successfully.\n"
                                    f"Technical Details: {tech_details}\n"
                                    "Configuration implementation and verification completed."
                                )
                                self._update_work_notes("sc_task", sctask_sys_id, success_work_note)
                                logger.info("SCTASK %s closed successfully", sctask_number)
                        else:
                            # Execution failed - close SCTASK as incomplete
                            if self._update_sc_task_state(sctask_sys_id, "4"):
                                failure_work_note = (
                                    "Change request execution failed.\n"
                                    f"Technical Details: {tech_details}\n"
                                    "CR has been moved to Review state for manual intervention.\n"
                                    "This task is being closed incomplete pending CR resolution."
                                )
                                self._update_work_notes("sc_task", sctask_sys_id, failure_work_note)
                                logger.info("SCTASK %s closed incomplete due to execution failure", sctask_number)
                        
                        # Phase 2 Terminal Work Notes Execution (SCTASK + CR Terminal Narratives)
                        if self.NarrativeType:
                            try:
                                self._post_narrative(
                                    event_type=self.NarrativeType.CR_SUCCESS if is_success else self.NarrativeType.CR_FAILURE,
                                    task_number=sctask_number,
                                    cr_sys_id=change_sys_id,
                                    cr_number=change_number,
                                    sctask_sys_id=sctask_sys_id,
                                    short_desc=meta.get("short_description", ""),
                                    desc=meta.get("description", ""),
                                    technical_details=tech_details
                                )
                            except Exception as e:
                                logger.exception("Failed to post terminal lifecycle narratives for %s: %s", change_number, e)
                        
                        # Update SCTASK on failure
                        if not is_success:
                            failure_work_note = (
                                "Change request execution failed.\n"
                                f"Technical Details: {tech_details}\n"
                                "CR has been moved to Review state for manual intervention.\n"
                                "This task is being closed incomplete pending CR resolution."
                            )
                            if self._update_sc_task_state(sctask_sys_id, "4"):
                                self._update_work_notes("sc_task", sctask_sys_id, failure_work_note)
                                logger.info(
                                    "SCTASK %s closed incomplete due to CR %s failure",
                                    sctask_number,
                                    change_number,
                                )
                            else:
                                logger.error(
                                    "Failed to close SCTASK %s after CR %s failure",
                                    sctask_number,
                                    change_number,
                                )
                    else:
                        logger.error("Failed to patch terminal state for %s: %s", change_number, patch_response.text)
                        meta["lifecycle_stage"] = "FailedToUpdate"
                    
                    self._save_tracking()

                elif live_state == "0":
                    if current_stage != "Review":
                        logger.info("Change Request %s entered Review phase.", change_number)
                        meta["lifecycle_stage"] = "Review"
                        self._save_tracking()

                    if meta.get("auto_close_ready"):
                        close_payload = {
                            "state": "3",
                            "close_code": "successful",
                            "close_notes": meta.get("close_notes_payload", "Automated configuration push completed successfully.")
                        }
                        logger.info(
                            "Closing CR %s with payload=%s",
                            change_number,
                            close_payload
                        )
                        close_response = requests.patch(
                            url,
                            auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
                            headers={"Content-Type": "application/json", "Accept": "application/json"},
                            json=close_payload,
                            verify=SERVICENOW_SSL_VERIFY,
                            timeout=SERVICENOW_TIMEOUT
                        )
                        logger.info(
                            "Close CR response status=%s body=%s",
                            close_response.status_code,
                            close_response.text
                        )
                        if close_response.status_code == 200:
                            logger.info("Change Request %s successfully transitioned to: Closed", change_number)
                            meta["lifecycle_stage"] = "Closed"
                            meta["auto_close_ready"] = False
                            self._append_stage_history(
                                meta,
                                "CHANGE_REQUEST_CLOSED",
                                "success",
                                "Change request closed successfully. Lifecycle complete.",
                            )

                            if self._update_sc_task_state(sctask_sys_id, "3"):
                                work_note = (
                                    "Change request completed successfully.\n"
                                    "Configuration implementation and verification completed.\n"
                                    "Associated task automatically closed."
                                )
                                self._update_work_notes("sc_task", sctask_sys_id, work_note)
                                logger.info(
                                    "SCTASK %s closed successfully after CR %s completion",
                                    sctask_number,
                                    change_number,
                                )
                            else:
                                logger.error(
                                    "Failed to close SCTASK %s after CR %s completion",
                                    sctask_number,
                                    change_number,
                                )

                            self._save_tracking()
                        else:
                            logger.error("Failed to close %s from Review state: %s", change_number, close_response.text)

                # -------------------------------------------------------------
                # CR ALREADY CLOSED IN SERVICENOW (state=3) but local stage
                # hasn't caught up — sync local state to Closed.
                # This handles restarts, race conditions, or stuck Review entries.
                # -------------------------------------------------------------
                elif live_state == "3":
                    if current_stage != "Closed":
                        logger.info(
                            "Change Request %s is already Closed in ServiceNow. "
                            "Syncing local lifecycle_stage to Closed.",
                            change_number,
                        )
                        meta["lifecycle_stage"] = "Closed"
                        meta["auto_close_ready"] = False
                        self._append_stage_history(
                            meta,
                            "CHANGE_REQUEST_CLOSED",
                            "success",
                            "Change request confirmed closed in ServiceNow. Local state synchronised.",
                        )
                        self._save_tracking()

            except Exception as e:
                logger.error("Error during lifecycle loop reconciliation for %s: %s", change_number, e)