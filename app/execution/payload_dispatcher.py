"""
Payload Dispatcher

Responsibilities:
- validate payload structure
- forward payload
- provide optional dry-run mode
"""

from __future__ import annotations

import copy
import json
import logging

from typing import Callable
from typing import Dict
from typing import Optional


logger = logging.getLogger(__name__)


ExecutionEngineFn = Callable[[Dict], None]


class PayloadDispatcher:

    REQUIRED_KEYS = {

        "operation",
        "payload"
    }

    def __init__(

        self,

        execution_engine:
        Optional[
            ExecutionEngineFn
        ] = None,

        dry_run: bool=False

    ):

        self.dry_run=dry_run


        self._engine=(

            execution_engine

            if execution_engine

            else

            self._default_engine
        )


        if not callable(
            self._engine
        ):

            raise TypeError(

                "execution_engine "
                "must be callable"
            )


    # ---------------------------------------------------
    # Public
    # ---------------------------------------------------

    def dispatch(

        self,
        payload: Dict

    )->None:

        self._validate(
            payload
        )


        safe_payload=(

            copy.deepcopy(
                payload
            )
        )


        operation=(

            safe_payload[
                "operation"
            ]
        )


        logger.info(

            "Dispatching payload "
            "(operation=%s)",

            operation
        )


        logger.debug(

            "Payload:\n%s",

            json.dumps(

                safe_payload,

                indent=2
            )
        )


        try:

            self._engine(
                safe_payload
            )

        except Exception:

            logger.exception(

                "Payload dispatch failed "
                "(operation=%s)",

                operation
            )

            raise


        logger.info(

            "Payload dispatched "
            "successfully "
            "(operation=%s)",

            operation
        )


    # ---------------------------------------------------
    # Validation
    # ---------------------------------------------------

    def _validate(

        self,
        payload: Dict

    )->None:

        if not isinstance(

            payload,
            dict

        ):

            raise ValueError(

                "Payload must "
                "be dictionary"
            )


        missing=(

            self.REQUIRED_KEYS

            -

            set(
                payload.keys()
            )
        )


        if missing:

            raise ValueError(

                f"Payload missing: "
                f"{sorted(missing)}"
            )


        if not isinstance(

            payload.get(
                "operation"
            ),

            str
        ):

            raise ValueError(

                "'operation' "
                "must be string"
            )


        if not isinstance(

            payload.get(
                "payload"
            ),

            dict
        ):

            raise ValueError(

                "'payload' "
                "must be dictionary"
            )


    # ---------------------------------------------------
    # Dry Run
    # ---------------------------------------------------

    @staticmethod
    def _default_engine(

        payload: Dict

    )->None:

        operation=(

            payload.get(

                "operation",

                "unknown"
            )
        )


        logger.info(

            "[DRY RUN] "
            "Execution engine "
            "received payload "
            "(operation=%s)",

            operation
        )


        logger.info(

            "\n%s\n%s\n%s\n%s\n%s",

            "="*70,

            f"DRY RUN "
            f"[operation={operation}]",

            "="*70,

            json.dumps(

                payload,
                indent=2
            ),

            "="*70
        )