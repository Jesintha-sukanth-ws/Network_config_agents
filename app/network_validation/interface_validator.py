"""
Interface Validator
"""

import re


class InterfaceValidator:

    INTERFACE_PATTERNS = [

        r"^Gi\d+/\d+/\d+$",

        r"^Fa\d+/\d+$",

        r"^Te\d+/\d+/\d+$",

        r"^Eth\d+/\d+$"
    ]

    VALID_SPEEDS = [
        10,
        100,
        1000,
        "auto"
    ]

    VALID_DUPLEX = [
        "auto",
        "full",
        "half"
    ]

    MAX_DESCRIPTION_LENGTH = 240

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

    def validate_interface_operation(
        self,
        intent_type,
        parameters,
        step_number
    ):

        errors = []

        interface = parameters.get(
            "interface"
        )

        if interface is not None:

            errors.extend(

                self.validate_interface_name(
                    interface,
                    intent_type,
                    step_number
                )
            )

        if intent_type == "configure_allowed_vlans":

            errors.extend(

                self.validate_allowed_vlans(
                    parameters,
                    step_number
                )
            )

        elif intent_type == "set_native_vlan":

            errors.extend(

                self.validate_native_vlan(
                    parameters,
                    step_number
                )
            )

        elif (

            intent_type
            ==
            "configure_interface_description"

        ):

            errors.extend(

                self.validate_description(
                    parameters,
                    step_number
                )
            )

        elif intent_type == "configure_speed":

            errors.extend(

                self.validate_speed(
                    parameters,
                    step_number
                )
            )

        elif intent_type == "configure_duplex":

            errors.extend(

                self.validate_duplex(
                    parameters,
                    step_number
                )
            )

        return errors

    def validate_interface_name(
        self,
        interface,
        intent_type,
        step_number
    ):

        errors = []

        if not isinstance(
            interface,
            str
        ):

            errors.append(

                self.build_error(
                    error_type="invalid_interface_type",
                    step=step_number,
                    intent_type=intent_type,
                    parameter="interface",
                    message="interface must be string"
                )
            )

            return errors

        valid = any(

            re.match(
                pattern,
                interface
            )

            for pattern
            in self.INTERFACE_PATTERNS
        )

        if not valid:

            errors.append(

                self.build_error(
                    error_type="invalid_interface_format",
                    step=step_number,
                    intent_type=intent_type,
                    parameter="interface",
                    message="invalid Cisco interface format"
                )
            )

        return errors

    def validate_allowed_vlans(
        self,
        parameters,
        step_number
    ):

        errors = []

        allowed_vlans = parameters.get(
            "allowed_vlans"
        )

        if not isinstance(
            allowed_vlans,
            list
        ):

            errors.append(

                self.build_error(
                    error_type="invalid_allowed_vlans",
                    step=step_number,
                    parameter="allowed_vlans",
                    message="allowed_vlans must be list"
                )
            )

            return errors

        for vlan in allowed_vlans:

            if not isinstance(
                vlan,
                int
            ):

                errors.append(

                    self.build_error(
                        error_type="invalid_allowed_vlan",
                        step=step_number,
                        parameter="allowed_vlans",
                        message="allowed_vlans must contain integers"
                    )
                )

        return errors

    def validate_native_vlan(
        self,
        parameters,
        step_number
    ):

        errors = []

        native_vlan = parameters.get(
            "native_vlan"
        )

        if not isinstance(
            native_vlan,
            int
        ):

            errors.append(

                self.build_error(
                    error_type="invalid_native_vlan",
                    step=step_number,
                    parameter="native_vlan",
                    message="native_vlan must be integer"
                )
            )

        return errors

    def validate_description(
        self,
        parameters,
        step_number
    ):

        errors = []

        description = parameters.get(
            "description"
        )

        if not isinstance(
            description,
            str
        ):

            errors.append(

                self.build_error(
                    error_type="invalid_description",
                    step=step_number,
                    parameter="description",
                    message="description must be string"
                )
            )

            return errors

        if len(description) > self.MAX_DESCRIPTION_LENGTH:

            errors.append(

                self.build_error(
                    error_type="description_too_long",
                    step=step_number,
                    parameter="description",
                    message="description too long"
                )
            )

        return errors

    def validate_speed(
        self,
        parameters,
        step_number
    ):

        errors = []

        speed = parameters.get(
            "speed"
        )

        if speed not in self.VALID_SPEEDS:

            errors.append(

                self.build_error(
                    error_type="invalid_speed",
                    step=step_number,
                    parameter="speed",
                    message="invalid speed"
                )
            )

        return errors

    def validate_duplex(
        self,
        parameters,
        step_number
    ):

        errors = []

        duplex = parameters.get(
            "duplex"
        )

        if duplex not in self.VALID_DUPLEX:

            errors.append(

                self.build_error(
                    error_type="invalid_duplex",
                    step=step_number,
                    parameter="duplex",
                    message="invalid duplex"
                )
            )

        return errors