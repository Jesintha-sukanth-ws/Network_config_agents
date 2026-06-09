"""
Dashboard Routes

Read-only API endpoints for the Operations Dashboard.
Uses existing data only - no new automation capabilities.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

from app.dashboard.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])
dashboard_service = DashboardService()

# Static file serving
@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the main dashboard HTML page."""
    static_dir = Path("app/static")
    dashboard_html = static_dir / "dashboard.html"
    
    if not dashboard_html.exists():
        raise HTTPException(status_code=404, detail="Dashboard page not found")
    
    return HTMLResponse(content=dashboard_html.read_text(encoding='utf-8'))

@dashboard_router.get("/static/{filename}")
async def serve_static(filename: str):
    """Serve static assets (CSS, JS, images)."""
    static_dir = Path("app/static")
    file_path = static_dir / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Set appropriate content type
    content_type = "text/plain"
    if filename.endswith('.css'):
        content_type = "text/css"
    elif filename.endswith('.js'):
        content_type = "application/javascript"
    elif filename.endswith('.html'):
        content_type = "text/html"
    
    return FileResponse(file_path, media_type=content_type)

# Dashboard API endpoints
@dashboard_router.get("/api/active")
async def get_active_task():
    """Get currently active task information."""
    try:
        active_task = dashboard_service.get_active_task()
        return {
            "active": active_task,
            "has_active": active_task is not None
        }
    except Exception as e:
        logger.error("Failed to get active task: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve active task")

@dashboard_router.get("/api/history")
async def get_task_history():
    """Get historical task execution data."""
    try:
        history = dashboard_service.get_task_history()
        return {
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error("Failed to get task history: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve task history")

@dashboard_router.get("/api/history/{sctask}")
async def get_task_details(sctask: str):
    """Get detailed execution information for a specific task."""
    try:
        task_details = dashboard_service.get_task_details(sctask)
        if not task_details:
            raise HTTPException(status_code=404, detail=f"Task {sctask} not found")
        
        return task_details
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task details for %s: %s", sctask, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve task details")

@dashboard_router.get("/api/timeline")
async def get_timeline():
    """Get chronological timeline of all automation events."""
    try:
        events = dashboard_service.get_timeline_events()
        return {
            "events": events,
            "count": len(events)
        }
    except Exception as e:
        logger.error("Failed to get timeline: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve timeline")

@dashboard_router.get("/api/metrics")
async def get_metrics():
    """Get calculated automation metrics from historical data."""
    try:
        metrics = dashboard_service.get_metrics()
        return metrics
    except Exception as e:
        logger.error("Failed to get metrics: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")

@dashboard_router.get("/api/pipeline/{sctask}")
async def get_pipeline_status(sctask: str):
    """Get detailed pipeline status for a specific task."""
    try:
        pipeline_status = dashboard_service.get_pipeline_status(sctask)
        if not pipeline_status:
            raise HTTPException(status_code=404, detail=f"Pipeline status for {sctask} not found")
        
        return pipeline_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get pipeline status for %s: %s", sctask, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve pipeline status")

@dashboard_router.get("/api/health")
async def dashboard_health():
    """Dashboard health check endpoint."""
    try:
        # Test basic functionality
        metrics = dashboard_service.get_metrics()
        active = dashboard_service.get_active_task()
        
        return {
            "status": "healthy",
            "dashboard_service": "operational",
            "data_source": "cr_tracking.json",
            "total_tasks": metrics.get("total_tasks", 0),
            "has_active_task": active is not None
        }
    except Exception as e:
        logger.error("Dashboard health check failed: %s", e)
        return {
            "status": "degraded", 
            "error": str(e)
        }