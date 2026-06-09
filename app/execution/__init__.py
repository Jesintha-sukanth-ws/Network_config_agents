"""
Execution Module - Final Output and Logging

This module handles the final dispatch of generated payloads,
including output formatting, logging, audit trails, and result validation.

Main Components:
- PayloadDispatcher: Final output/logging layer

Usage:
    from app.execution import PayloadDispatcher
    
    # Initialize dispatcher
    dispatcher = PayloadDispatcher(output_directory="./output")
    
    # Dispatch a payload
    result = dispatcher.dispatch_payload(
        payload={"config": {"vlan": {"id": 100}}},
        payload_type="network",
        target="switch-01"
    )
    
    # Get dispatch statistics
    stats = dispatcher.get_dispatch_stats()
"""

from .payload_dispatcher import PayloadDispatcher
from .push_config import PushConfigExecutor
from .execution_status import ExecutionStatusVerifier

__all__ = [
    "PayloadDispatcher",
    "PushConfigExecutor",
    "ExecutionStatusVerifier",
]

__version__ = "1.0.0"