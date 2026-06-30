import re
from typing import Dict, List


class VlanValidator:
    def can_handle(self, intent_type: str) -> bool:
        return intent_type in {
            "create_vlan",
            "delete_vlan"
        }

    def validate(
        self,
        intent_type: str,
        params: Dict,
        step: int
    ) -> List[Dict]:

        errors = []

        vlan_rules = {}

        vlan_id = params.get("vlan_id")
        name = params.get("name")

        # -----------------------------
        # Type validation
        # -----------------------------

        if vlan_id is not None:

            if not isinstance(vlan_id, int):

                errors.append({
                    "error_type": "invalid_vlan_type",
                    "step": step,
                    "field": "vlan_id",
                    "message": "VLAN ID must be integer"
                })

                return errors

        if vlan_id == 1 and intent_type == "delete_vlan":

            errors.append({
                "error_type": "default_vlan_protection",
                "step": step,
                "field": "vlan_id",
                "message": "Default VLAN 1 cannot be deleted"
            })

        vlan_range = vlan_rules.get("vlan_range")

        if vlan_id is not None and vlan_range:

            min_vlan, max_vlan = vlan_range

            if not (min_vlan <= vlan_id <= max_vlan):

                errors.append({
                    "error_type": "invalid_vlan_range",
                    "step": step,
                    "field": "vlan_id",
                    "message": (
                        f"VLAN ID {vlan_id} "
                        f"outside allowed range "
                        f"{min_vlan}-{max_vlan}"
                    )
                })

        reserved_vlans = vlan_rules.get(
            "reserved_vlans",
            []
        )

        if (
            intent_type == "create_vlan"
            and vlan_id in reserved_vlans
        ):

            errors.append({
                "error_type": "reserved_vlan",
                "step": step,
                "field": "vlan_id",
                "message": (
                    f"VLAN {vlan_id} "
                    f"cannot be used"
                )
            })

        if name:

            max_length = vlan_rules.get(
                "max_vlan_name_length"
            )

            regex = vlan_rules.get(
                "vlan_name_regex"
            )

            if (
                max_length
                and len(name) > max_length
            ):

                errors.append({
                    "error_type": "name_too_long",
                    "step": step,
                    "field": "name",
                    "message": (
                        f"VLAN name exceeds "
                        f"{max_length} characters"
                    )
                })

            if (
                regex
                and not re.fullmatch(regex, name)
            ):

                errors.append({
                    "error_type": "invalid_vlan_name",
                    "step": step,
                    "field": "name",
                    "message": (
                        "VLAN name format is invalid"
                    )
                })

        return errors