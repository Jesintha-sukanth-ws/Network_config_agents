"""
Dashboard Service

Provides read-only access to existing automation data for the Operations Dashboard.
Uses only existing data sources - no new automation behavior introduced.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class DashboardService:
    """Read-only service to aggregate existing automation data for dashboard display."""
    
    def __init__(self, tracking_file: str = "data/tracking/cr_tracking.json"):
        self.tracking_file = tracking_file
    
    def _load_tracking_data(self) -> Dict[str, Any]:
        """Load existing tracking data - no modifications."""
        if not os.path.exists(self.tracking_file):
            return {"tasks": {}}
        
        try:
            if os.path.getsize(self.tracking_file) == 0:
                return {"tasks": {}}
            
            with open(self.tracking_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load tracking data: %s", e)
            return {"tasks": {}}
    
    def get_active_task(self) -> Optional[Dict[str, Any]]:
        """Get currently active task from existing tracking data."""
        tracking_data = self._load_tracking_data()
        tasks = tracking_data.get("tasks", {})
        
        # Find the most recent task that's not in "Closed" state
        active_task = None
        latest_timestamp = None
        
        for task_id, task_data in tasks.items():
            stage = task_data.get("lifecycle_stage", "").lower()
            if stage != "closed":
                # Get latest timestamp from stage_history
                stage_history = task_data.get("stage_history", [])
                if stage_history:
                    last_event = stage_history[-1]
                    event_time = last_event.get("timestamp")
                    if event_time and (latest_timestamp is None or event_time > latest_timestamp):
                        latest_timestamp = event_time
                        active_task = {
                            "task_id": task_id,
                            "sctask": task_data.get("task_number"),
                            "cr": task_data.get("change_number"),
                            "stage": stage,
                            "status": last_event.get("status"),
                            "short_description": task_data.get("short_description"),
                            "device": task_data.get("device_data", {}).get("device_name"),
                            "started_at": stage_history[0].get("timestamp") if stage_history else None,
                            "last_update": event_time
                        }
        
        return active_task
    
    def get_task_history(self) -> List[Dict[str, Any]]:
        """Get completed task history from existing tracking data."""
        tracking_data = self._load_tracking_data()
        tasks = tracking_data.get("tasks", {})
        
        history = []
        for task_id, task_data in tasks.items():
            stage_history = task_data.get("stage_history", [])
            start_time = stage_history[0].get("timestamp") if stage_history else None
            end_time = stage_history[-1].get("timestamp") if stage_history else None
            
            history.append({
                "task_id": task_id,
                "sctask": task_data.get("task_number"),
                "cr": task_data.get("change_number"),
                "short_description": task_data.get("short_description"),
                "device": task_data.get("device_data", {}).get("device_name"),
                "lifecycle_stage": task_data.get("lifecycle_stage"),
                "status": stage_history[-1].get("status") if stage_history else "unknown",
                "started_at": start_time,
                "completed_at": end_time,
                "total_stages": len(stage_history)
            })
        
        # Sort by completion time, most recent first
        history.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
        return history
    
    def get_task_details(self, sctask: str) -> Optional[Dict[str, Any]]:
        """Get detailed execution information for a specific task."""
        tracking_data = self._load_tracking_data()
        tasks = tracking_data.get("tasks", {})
        
        for task_id, task_data in tasks.items():
            if task_data.get("task_number") == sctask:
                return {
                    "task_id": task_id,
                    "sctask": sctask,
                    "cr": task_data.get("change_number"),
                    "short_description": task_data.get("short_description"),
                    "description": task_data.get("description"),
                    "device_data": task_data.get("device_data", {}),
                    "policy": task_data.get("policy", {}),
                    "execution_plan": task_data.get("execution_plan", []),
                    "generated_payloads": task_data.get("generated_payloads", []),
                    "verification_plan": task_data.get("verification_plan", []),
                    "stage_history": task_data.get("stage_history", []),
                    "lifecycle_stage": task_data.get("lifecycle_stage"),
                    "auto_close_ready": task_data.get("auto_close_ready", False)
                }
        
        return None
    
    def get_timeline_events(self) -> List[Dict[str, Any]]:
        """Get chronological timeline of all events from existing data."""
        tracking_data = self._load_tracking_data()
        tasks = tracking_data.get("tasks", {})
        
        events = []
        for task_id, task_data in tasks.items():
            sctask = task_data.get("task_number")
            cr = task_data.get("change_number")
            device = task_data.get("device_data", {}).get("device_name")
            
            for event in task_data.get("stage_history", []):
                events.append({
                    "timestamp": event.get("timestamp"),
                    "sctask": sctask,
                    "cr": cr,
                    "device": device,
                    "stage": event.get("stage"),
                    "status": event.get("status"),
                    "message": event.get("message"),
                    "severity": self._get_event_severity(event.get("status"))
                })
        
        # Sort chronologically, most recent first
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return events
    
    def get_metrics(self) -> Dict[str, Any]:
        """Calculate metrics from existing historical data."""
        tracking_data = self._load_tracking_data()
        tasks = tracking_data.get("tasks", {})
        
        total_tasks = len(tasks)
        successful_tasks = 0
        failed_tasks = 0
        closed_tasks = 0
        
        device_counts = {}
        operation_counts = {}
        
        for task_data in tasks.values():
            # Count by lifecycle stage
            stage = task_data.get("lifecycle_stage", "").lower()
            if stage == "closed":
                closed_tasks += 1
                
                # Determine success/failure from stage history
                stage_history = task_data.get("stage_history", [])
                final_status = stage_history[-1].get("status") if stage_history else "unknown"
                if final_status == "success":
                    successful_tasks += 1
                else:
                    failed_tasks += 1
            
            # Count by device
            device_name = task_data.get("device_data", {}).get("device_name")
            if device_name:
                device_counts[device_name] = device_counts.get(device_name, 0) + 1
            
            # Count by operations
            for payload in task_data.get("generated_payloads", []):
                operation = payload.get("payload_data", {}).get("operation")
                if operation:
                    operation_counts[operation] = operation_counts.get(operation, 0) + 1
        
        success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "closed_tasks": closed_tasks,
            "in_progress_tasks": total_tasks - closed_tasks,
            "success_rate": round(success_rate, 1),
            "device_breakdown": device_counts,
            "operation_breakdown": operation_counts,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    def get_pipeline_status(self, sctask: str) -> Dict[str, Any]:
        """Get detailed pipeline status for a specific task."""
        task_details = self.get_task_details(sctask)
        if not task_details:
            return {}
        
        # Map stage history to pipeline stages
        stage_history = task_details.get("stage_history", [])
        
        pipeline_stages = [
            "SCTASK_RECEIVED",
            "CHANGE_REQUEST_CREATED", 
            "CONFIGURATION_EXECUTING",
            "CONFIGURATION_VERIFIED",
            "CHANGE_REQUEST_CLOSED"
        ]
        
        pipeline_status = {}
        for stage in pipeline_stages:
            # Find if this stage appears in history
            stage_event = next((event for event in stage_history if event.get("stage") == stage), None)
            
            if stage_event:
                pipeline_status[stage] = {
                    "status": stage_event.get("status"),
                    "timestamp": stage_event.get("timestamp"),
                    "message": stage_event.get("message"),
                    "completed": True
                }
            else:
                pipeline_status[stage] = {
                    "status": "pending",
                    "timestamp": None,
                    "message": "Waiting...",
                    "completed": False
                }
        
        return {
            "sctask": sctask,
            "pipeline_stages": pipeline_status,
            "current_stage": task_details.get("lifecycle_stage"),
            "execution_plan": task_details.get("execution_plan", []),
            "generated_payloads": task_details.get("generated_payloads", [])
        }
    
    def _get_event_severity(self, status: str) -> str:
        """Map status to severity level for UI display."""
        status_lower = (status or "").lower()
        if status_lower == "success":
            return "success"
        elif status_lower in ["failed", "error"]:
            return "error"
        elif status_lower in ["warning", "retry"]:
            return "warning"
        else:
            return "info"