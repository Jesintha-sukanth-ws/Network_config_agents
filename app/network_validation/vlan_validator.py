

import re


class VlanValidator:

    RESERVED_VLANS = [
        1002,
        1003,
        1004,
        1005
    ]

    VLAN_MIN = 1
    VLAN_MAX = 4094

    MAX_VLAN_NAME_LENGTH = 32

    VLAN_NAME_PATTERN = r"^[a-zA-Z0-9_\-]+$"

    def build_error(
        self,
        error_type: str,
        step: int,
        parameter: str,
        message: str,
        intent_type: str = None
    ) -> dict:
        """
        Build a standardized error dictionary.
        """
        error = {
            "error_type": error_type,
            "step": step,
            "parameter": parameter,
            "message": message
        }
        
        if intent_type:
            error["intent_type"] = intent_type
            
        return error

    def validate_vlan_operation(
        self,
        intent_type,
        parameters,
        step_number
    ):

        errors = []

        vlan_id = parameters.get(
            "vlan_id"
        )

        name = parameters.get(
            "name"
        )

        if vlan_id is not None:

            errors.extend(

                self.validate_vlan_id(
                    vlan_id,
                    intent_type,
                    step_number
                )
            )

        if name is not None:

            errors.extend(

                self.validate_vlan_name(
                    name,
                    step_number
                )
            )

        return errors

    def validate_vlan_id(
        self,
        vlan_id,
        intent_type,
        step_number
    ):

        errors = []

        if not isinstance(
            vlan_id,
            int
        ):

            errors.append(

                self.build_error(
                    error_type="invalid_vlan_type",
                    step=step_number,
                    intent_type=intent_type,
                    parameter="vlan_id",
                    message="vlan_id must be integer"
                )
            )

            return errors

        if vlan_id < self.VLAN_MIN:

            errors.append(

                self.build_error(
                    error_type="invalid_vlan_range",
                    step=step_number,
                    intent_type=intent_type,
                    parameter="vlan_id",
                    message="vlan_id below valid range"
                )
            )

        if vlan_id > self.VLAN_MAX:

            errors.append(

                self.build_error(
                    error_type="invalid_vlan_range",
                    step=step_number,
                    intent_type=intent_type,
                    parameter="vlan_id",
                    message="vlan_id exceeds valid range"
                )
            )

        if vlan_id in self.RESERVED_VLANS:

            errors.append(

                self.build_error(
                    error_type="reserved_vlan",
                    step=step_number,
                    intent_type=intent_type,
                    parameter="vlan_id",
                    message="reserved VLAN cannot be modified"
                )
            )

        if vlan_id == 1:

            if intent_type == "delete_vlan":

                errors.append(

                    self.build_error(
                        error_type="default_vlan",
                        step=step_number,
                        intent_type=intent_type,
                        parameter="vlan_id",
                        message="default VLAN cannot be deleted"
                    )
                )

        return errors

    def validate_vlan_name(
        self,
        name,
        step_number
    ):

        errors = []

        if not isinstance(
            name,
            str
        ):

            errors.append(

                self.build_error(
                    error_type="invalid_vlan_name_type",
                    step=step_number,
                    parameter="name",
                    message="VLAN name must be string"
                )
            )

            return errors

        if not name.strip():

            errors.append(

                self.build_error(
                    error_type="empty_vlan_name",
                    step=step_number,
                    parameter="name",
                    message="VLAN name cannot be empty"
                )
            )

        if len(name) > self.MAX_VLAN_NAME_LENGTH:

            errors.append(

                self.build_error(
                    error_type="vlan_name_too_long",
                    step=step_number,
                    parameter="name",
                    message="VLAN name too long"
                )
            )

        if not re.match(
            self.VLAN_NAME_PATTERN,
            name
        ):

            errors.append(

                self.build_error(
                    error_type="invalid_vlan_name",
                    step=step_number,
                    parameter="name",
                    message="invalid VLAN name characters"
                )
            )

        return errors