from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

from config.settings import DEVICE_CREDENTIALS

logger = logging.getLogger(__name__)


class ConnectionService:
    """
    Handles device connection resolution.

    Responsibilities:
    - Load device capabilities
    - Resolve credentials
    - Build standardized connection contract
    """


    def __init__(self) -> None:

        self._load_capabilities()


    @staticmethod
    @lru_cache(maxsize=1)
    def _load_capabilities() -> Dict[str, Any]:
        """
        Load and cache device capabilities.
        """

        path = (

            Path(__file__)
            .resolve()
            .parent
            /
            "device_capabilities.json"
        )

        try:

            with open(

                path,
                "r",
                encoding="utf-8"

            ) as file:

                return json.load(
                    file
                )

        except Exception as e:

            logger.critical(

                "Failed loading "
                "device capabilities: %s",

                e
            )

            raise RuntimeError(

                f"Connection initialization "
                f"failed: {e}"
            )


    def connect(

        self,

        device: Dict[str, Any]

    ) -> Dict[str, Any]:

        """
        Resolve device connection details.
        """


        vendor = device.get(
            "vendor"
        )

        os_type = device.get(
            "os_type"
        )


        capabilities = (

            self._load_capabilities()
        )


        capability = (

            capabilities
            .get(vendor,{})
            .get(os_type)
        )


        if not capability:

            raise ValueError(

                f"No capability "
                f"for {vendor} "
                f"{os_type}"
            )


        credentials = (

            device.get(
                "credentials"
            )

            or

            DEVICE_CREDENTIALS.get(
                vendor
            )
        )


        if not credentials:

            raise ValueError(

                f"No credentials "
                f"for vendor: "
                f"{vendor}"
            )


        connection = {

            "host":
            device.get(
                "management_host"
            ),

            "vendor":
            vendor,

            "os_type":
            os_type,

            "connection_method":
            capability.get(
                "preferred_connection"
            ),

            "port":
            capability.get(
                "default_port"
            ),

            "username":
            credentials.get(
                "username"
            ),

            "password":
            credentials.get(
                "password"
            ),

            # Carry the full capability block so the device-state
            # layer can resolve state_endpoints / state_commands
            # without re-loading the JSON.
            "capability":
            capability
        }


        # 'capability' is a dict and may legitimately be empty for
        # placeholder vendors; it is therefore excluded from the
        # missing-required-field check below.
        missing = [

            key

            for key,value
            in connection.items()

            if key != "capability"
            and not value
        ]


        if missing:

            raise ValueError(

                f"Incomplete "
                f"connection data: "
                f"{missing}"
            )


        logger.info(

            "Connection contract "
            "prepared for %s",

            connection[
                "host"
            ]
        )


        return connection