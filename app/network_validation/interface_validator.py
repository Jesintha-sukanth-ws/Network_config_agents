import re
from typing import Dict, List

from app.network_validation.base_validator import BaseValidator
from app.registry.intent_registry import get_intent_schema


class InterfaceValidator(BaseValidator):


    def can_handle(self, intent_type: str) -> bool:
        return intent_type in {
            "configure_access_port",
            "configure_trunk_port",
            "configure_interface_status",
        }


    def validate(
        self,
        intent_type: str,
        params: Dict,
        step: int,
        policy: Dict
    ) -> List[Dict]:

        schema = get_intent_schema(intent_type)

        if not schema:

            return [
                self.build_error(
                    error_type="unknown_intent",
                    message=f"Unsupported intent: {intent_type}",
                    step=step,
                    parameter="intent_type",
                )
            ]

        dispatch = {

            "configure_access_port":
                self.validate_access,

            "configure_trunk_port":
                self.validate_trunk,

            "configure_interface_status":
                self.validate_status
        }

        handler = dispatch.get(intent_type)

        return handler(
            params,
            step,
            policy
        ) if handler else []


    def validate_interface(
        self,
        interface,
        description,
        step,
        policy
    ):

        errors = []

        if not interface:

            errors.append(
                self.build_error(
                    error_type="missing_interface",
                    message="Required",
                    step=step,
                    parameter="interface",
                )
            )

            return errors


        interface_rules = policy.get(
            "interface_rules",
            {}
        )

        pattern = interface_rules.get(
            "interface_name_regex"
        )


        if pattern:

            if not re.fullmatch(
                pattern,
                interface
            ):

                errors.append(
                    self.build_error(
                        error_type="invalid_interface",
                        message=f"Invalid interface format: {interface}",
                        step=step,
                        parameter="interface",
                    )
                )


        max_description = interface_rules.get(
            "max_interface_description"
        )


        if (
            description
            and
            max_description
            and
            len(description) > max_description
        ):

            errors.append(
                self.build_error(
                    error_type="description_too_long",
                    message=f"Description exceeds {max_description} characters",
                    step=step,
                    parameter="description",
                )
            )

        return errors


    def validate_access(
        self,
        params,
        step,
        policy
    ):

        return self.validate_interface(
            params.get("interface"),
            params.get("description"),
            step,
            policy
        )


    def validate_trunk(
        self,
        params,
        step,
        policy
    ):

        errors = []

        errors.extend(
            self.validate_interface(
                params.get("interface"),
                params.get("description"),
                step,
                policy
            )
        )

        native_vlan = params.get(
            "native_vlan"
        )

        invalid_native = (
            policy.get(
                "trunk_rules",
                {}
            ).get(
                "invalid_native_vlans",
                []
            )
        )

        if native_vlan in invalid_native:

            errors.append(
                self.build_error(
                    error_type="invalid_native_vlan",
                    message=f"{native_vlan} cannot be used",
                    step=step,
                    parameter="native_vlan",
                )
            )

        return errors


    def validate_status(
        self,
        params,
        step,
        policy
    ):

        errors = []

        errors.extend(
            self.validate_interface(
                params.get("interface"),
                None,
                step,
                policy
            )
        )

        state = params.get(
            "administrative_state"
        )

        state = state.upper() if state else None

        if state not in {
            "UP",
            "DOWN"
        }:

            errors.append(
                self.build_error(
                    error_type="invalid_state",
                    message="Must be UP or DOWN",
                    step=step,
                    parameter="administrative_state",
                )
            )

        return errors
