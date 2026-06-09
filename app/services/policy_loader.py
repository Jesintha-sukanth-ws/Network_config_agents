"""
policy_loader.py

Responsibilities:
- Load policy JSON
- Cache policy data
- Validate policy structure
- Provide policy section access

Does NOT:
- Resolve policy selection
- Perform business validation
- Validate device state
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any


logger = logging.getLogger(__name__)


@lru_cache(maxsize=20)
def _load_policy_file(policy_path: str) -> Dict[str, Any]:
    """
    Cache based on file path
    instead of object instance.
    """

    with open(policy_path,"r",encoding="utf-8") as file:
        return json.load(file)


class PolicyLoader:

    REQUIRED_SECTIONS = (

        "schema_version",

        "vendor",

        "os",

        "model_family",

        "vlan_rules",

        "interface_rules",

        # "trunk_rules"
    )


    def __init__(self,policy_path: Path):

        self.policy_path = Path(policy_path)
        self.rules = self._load()


    def _load(self) -> Dict[str, Any]:

        if not self.policy_path.exists():

            raise FileNotFoundError(

                f"Policy not found: "
                f"{self.policy_path}"
            )


        try:

            data = (_load_policy_file(str(self.policy_path)))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid policy JSON: "f"{e}")
        except Exception as e:
            raise RuntimeError(f"Policy load failed: "f"{e}")
        self._validate(data)


        logger.info(

            "Loaded policy=%s",

            self.policy_path.name
        )

        return data


    def _validate(
        self,
        data: Dict[str, Any]
    ):

        missing = [

            section

            for section in
            self.REQUIRED_SECTIONS

            if section
            not in data
        ]


        if missing:

            raise ValueError(

                f"Missing policy sections: "
                f"{missing}"
            )


        structured_sections = [

            "vlan_rules",

            "interface_rules",

            "trunk_rules"
        ]


        for section in (structured_sections):

            if not isinstance(data.get(section),dict):
                raise ValueError(
                    f"{section} "
                    f"must be dict"
                )


    def get_rules(self,section: str) -> Dict:
        return self.rules.get(section,{})

    def get_vlan_rules(self) -> Dict:
        return self.get_rules("vlan_rules")

    def get_interface_rules(self) -> Dict:
        return self.get_rules("interface_rules")

    def get_trunk_rules(self) -> Dict:
        return self.get_rules("trunk_rules")

    def get_metadata(self) -> Dict:
        return {

            "schema_version":self.rules.get("schema_version"),
            "vendor":self.rules.get("vendor"),
            "os":self.rules.get("os"),
            "model_family":self.rules.get("model_family")
        }