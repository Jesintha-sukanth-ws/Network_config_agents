"""
policy_resolver.py

Responsibilities:
- Resolve policy family from inventory
- Load matching policy
- Return loaded policy
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional

from app.services.policy_loader import PolicyLoader


logger = logging.getLogger(__name__)


class PolicyResolver:

    def __init__(
        self,
        capability_file: Path = Path(
            "app/devices/device_capabilities.json"
        ),
        policy_directory: Path = Path(
            "data/policies"
        )
    ):

        self.policy_directory = Path(
            policy_directory
        )

        with open(

            capability_file,

            "r",

            encoding="utf-8"

        ) as file:

            self.capabilities = json.load(
                file
            )


    def resolve(
        self,
        device: Dict[str, Any]
    ) -> Dict[str, Any]:

        vendor = device.get(
            "vendor"
        )

        os_type = device.get(
            "os_type"
        )

        # Accept either 'model_number' or 'model' field from CMDB
        model_number = device.get(
            "model_number"
        ) or device.get(
            "model"
        )


        if not all([

            vendor,
            os_type,
            model_number

        ]):

            raise ValueError(

                "Missing required "
                "device information "
                "for policy resolution"
            )


        model_family = (

            self._resolve_model_family(

                vendor=vendor,

                os_type=os_type,

                model_number=model_number
            )
        )


        policy_name=(

            f"{vendor.lower()}_"

            f"{os_type.lower().replace('-','')}_"

            f"{model_family.lower()}.json"
        )


        policy_path=(

            self.policy_directory
            /
            policy_name
        )


        logger.info(

            "Resolved policy=%s",

            policy_name
        )


        return (

            PolicyLoader(
                policy_path
            )
            .rules
        )


    def _resolve_model_family(

        self,

        vendor:str,

        os_type:str,

        model_number:str

    )->str:

        os_capabilities=(

            self.capabilities
            .get(vendor,{})
            .get(os_type,{})
        )


        patterns=(

            os_capabilities.get(

                "model_family_patterns",

                []
            )
        )


        for entry in patterns:

            pattern=entry.get(
                "pattern"
            )

            family=entry.get(
                "family"
            )


            if (

                pattern
                and
                family
                and
                re.match(

                    pattern,

                    model_number,

                    re.IGNORECASE
                )
            ):

                logger.info(

                    "Resolved model=%s "
                    "to family=%s",

                    model_number,

                    family
                )

                return family


        default_family=(

            os_capabilities.get(

                "default_family"
            )
        )


        if default_family:

            logger.warning(

                "No family match "
                "for model=%s. "
                "Using default=%s",

                model_number,

                default_family
            )

            return default_family


        raise ValueError(

            f"No policy family "
            f"mapping found for "
            f"{vendor}/"
            f"{os_type}/"
            f"{model_number}"
        )