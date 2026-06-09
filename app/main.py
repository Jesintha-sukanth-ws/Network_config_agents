from __future__ import annotations

import threading
import logging
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI

from app.services.polling_service import poll_servicenow
from app.services.orchestrator_service import process_task
from app.dashboard.routes import dashboard_router


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    )
)

logger = logging.getLogger(__name__)


stop_event = threading.Event()


def polling_worker():
    """Background thread worker for ServiceNow polling."""
    try:
        poll_servicenow(stop_event=stop_event)
    except Exception:
        logger.exception("Polling service crashed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""

    logger.info("Starting application...")

    # Pre-initialize heavy services in main thread before starting polling
    # This ensures the embedding model and LLM are loaded once, not in the polling thread
    logger.info("Pre-initializing heavy services (RAG, LLM)...")
    from app.services.orchestrator_service import _get_payload_service
    _get_payload_service()  # Triggers lazy initialization in main thread
    logger.info("Heavy services initialized")

    # Start polling thread
    polling_thread = threading.Thread(
        target=polling_worker,
        daemon=True,
        name="servicenow-polling"
    )

    polling_thread.start()
    logger.info("Polling service started")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    stop_event.set()
    polling_thread.join(timeout=5)
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Network Orchestrator API",
    version="1.0.0",
    lifespan=lifespan
)

# Include dashboard routes
app.include_router(dashboard_router)


@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "services": {
            "api": "healthy",
            "orchestrator": "healthy",
            "polling": "running"
        }
    }


@app.post("/tasks/execute")
async def execute_task(task_data: Dict):
    """Execute a task directly via API."""
    return process_task(task_data)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
