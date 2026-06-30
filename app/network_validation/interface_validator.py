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
        step: int
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
            step
        ) if handler else []


    def validate_interface(
        self,
        interface,
        description,
        step
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

        return errors


    def validate_access(
        self,
        params,
        step
    ):

        return self.validate_interface(
            params.get("interface"),
            params.get("description"),
            step
        )


    def validate_trunk(
        self,
        params,
        step
    ):

        errors = []

        errors.extend(
            self.validate_interface(
                params.get("interface"),
                params.get("description"),
                step
            )
        )

        return errors


    def validate_status(
        self,
        params,
        step
    ):

        errors = []

        errors.extend(
            self.validate_interface(
                params.get("interface"),
                None,
                step
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
