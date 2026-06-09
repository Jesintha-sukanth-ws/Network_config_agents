"""
logger.py

Central orchestration logger.

Responsibilities:
- Standard orchestration formatting
- Step tracking
- Validation reporting
- Device summaries
- Execution summaries
- Exception logging
- Machine-parseable stage logging
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Dict, List, Optional


logger = logging.getLogger("orchestrator")


# -----------------------------------------------------------------------------
# Stage Logger - Machine-parseable entry/exit logging for pipeline stages
# -----------------------------------------------------------------------------

def _create_stage_logger() -> logging.Logger:
    
    _stage_logger = logging.getLogger("stage")
    
    if not _stage_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        handler.setFormatter(formatter)
        _stage_logger.addHandler(handler)
        _stage_logger.setLevel(logging.INFO)
        _stage_logger.propagate = False
    
    return _stage_logger


stage_logger = _create_stage_logger()


def safe_stage_log(level: str, message: str) -> None:
    """
    Safely log a stage message, ensuring logging failures cannot break pipeline execution.
    
    Args:
        level: Log level - 'info', 'error', or 'warning'
        message: The message to log
    """
    try:
        if level == "info":
            stage_logger.info(message)
        elif level == "error":
            stage_logger.error(message)
        elif level == "warning":
            stage_logger.warning(message)
        else:
            stage_logger.info(message)
    except Exception:
        # Never let logging break the pipeline
        pass


def log_stage_entry(stage_name: str) -> None:
    """
    Log entry into a pipeline stage.
    
    Args:
        stage_name: Name of the stage being entered
    """
    safe_stage_log("info", f"Entering {stage_name}")


def log_stage_completed(stage_name: str) -> None:
    """
    Log successful completion of a pipeline stage.
    
    Args:
        stage_name: Name of the stage that completed
    """
    safe_stage_log("info", f"Completed {stage_name}")


def log_stage_failed(stage_name: str) -> None:
    """
    Log failure of a pipeline stage.
    
    Args:
        stage_name: Name of the stage that failed
    """
    safe_stage_log("error", f"Failed {stage_name}")


def log_stage_skipped(stage_name: str, reason: str) -> None:
    """
    Log that a pipeline stage was skipped.
    
    Args:
        stage_name: Name of the stage that was skipped
        reason: Reason why the stage was skipped
    """
    safe_stage_log("info", f"Skipped {stage_name}: {reason}")


class OrchestrationLogger:

    def __init__(self):

        if not logger.handlers:

            handler = logging.StreamHandler(
                sys.stdout
            )

            formatter = logging.Formatter(
                "%(message)s"
            )

            handler.setFormatter(
                formatter
            )

            logger.addHandler(
                handler
            )

            logger.setLevel(
                logging.INFO
            )

            logger.propagate = False

    # ---------------------------------------------------------
    # General Sections
    # ---------------------------------------------------------

    @staticmethod
    def header(title: str):

        logger.info(
            "\n%s\n%s\n%s",
            "=" * 80,
            title.upper(),
            "=" * 80
        )

    @staticmethod
    def subheader(title: str):

        logger.info(
            "\n%s\n%s",
            title,
            "-" * 50
        )

    # ---------------------------------------------------------
    # Stage Visibility
    # ---------------------------------------------------------

    @staticmethod
    def kv_block(title: str, data=None) -> None:


        logger.info("\n%s", "-" * 80)
        logger.info(title.upper())
        logger.info("%s", "-" * 80)

        if data is None:
            return

        if isinstance(data, (dict, list)):
            logger.info(
                "%s",
                json.dumps(data, indent=2, default=str)
            )
        else:
            logger.info("%s", str(data))

    # ---------------------------------------------------------
    # Steps
    # ---------------------------------------------------------

    @staticmethod
    def step_start(
        step: int,
        total: int,
        name: str
    ):

        logger.info(
            "\n[%s/%s] %s",
            step,
            total,
            name
        )

    @staticmethod
    def step_success(
        message: str
    ):

        logger.info(
            "   ✓ %s",
            message
        )

    @staticmethod
    def step_failure(
        message: str
    ):

        logger.error(
            "   ✗ %s",
            message
        )

    @staticmethod
    def step_warning(
        message: str
    ):

        logger.warning(
            "   ⚠ %s",
            message
        )

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    @staticmethod
    def validation_failed(
        validation_type: str,
        errors: List[str]
    ):

        logger.error(
            "\nVALIDATION FAILED: %s",
            validation_type
        )

        for index,error in enumerate(
            errors[:5],
            start=1
        ):

            logger.error(
                "   %s. %s",
                index,
                error
            )

        if len(errors)>5:

            logger.error(
                "   ...and %s more",
                len(errors)-5
            )

    # ---------------------------------------------------------
    # Device
    # ---------------------------------------------------------

    @staticmethod
    def device_summary(
        facts: Dict
    ):

        info=facts.get(
            "device_info",
            {}
        )

        logger.info(
            "\nDEVICE SUMMARY"
        )

        logger.info(
            "-"*50
        )

        fields=[

            ("Hostname",
             info.get(
                 "hostname",
                 "N/A"
             )),

            ("Vendor",
             info.get(
                 "vendor",
                 "N/A"
             )),

            ("OS Type",
             info.get(
                 "os_type",
                 "N/A"
             )),

            ("OS Version",
             info.get(
                 "os_version",
                 "N/A"
             ))

        ]

        for label,value in fields:

            logger.info(
                "%-15s : %s",
                label,
                value
            )

    # ---------------------------------------------------------
    # Results
    # ---------------------------------------------------------

    @staticmethod
    def execution_results(
        results: List[Dict]
    ):

        logger.info(
            "\nEXECUTION RESULTS"
        )

        logger.info(
            "-"*50
        )

        for result in results:

            step=result.get(
                "step",
                "-"
            )

            operation=result.get(
                "operation",
                "-"
            )

            success=(
                result
                .get(
                    "push_result",
                    {}
                )
                .get(
                    "success",
                    False
                )
            )

            status=(
                "SUCCESS"
                if success
                else
                "FAILED"
            )

            logger.info(
                "Step %s [%s] → %s",
                step,
                operation,
                status
            )

    # ---------------------------------------------------------
    # Exceptions
    # ---------------------------------------------------------

    @staticmethod
    def exception(
        message: str
    ):

        logger.exception(
            message
        )


orchestrator_logger=(
    OrchestrationLogger()
)