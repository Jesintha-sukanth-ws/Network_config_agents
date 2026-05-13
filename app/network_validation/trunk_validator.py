"""
Trunk Validator

Validates Cisco trunk configuration rules based on:
- IEEE 802.1Q trunk behavior
- allowed VLAN semantics
- native VLAN constraints
- trunk mode configuration
- VLAN list validation

This validator ONLY handles trunk-related logic.

No live device checks.
No DTP negotiation validation.
No STP runtime validation.
No EtherChannel validation.
"""


class TrunkValidator:

    """
    Cisco trunk validator
    """

    # =====================================================
    # VLAN LIMITS
    # =====================================================

    VLAN_MIN = 1

    VLAN_MAX = 4094

    # =====================================================
    # RESERVED VLANS
    # =====================================================

    RESERVED_VLANS = [
        1002,
        1003,
        1004,
        1005
    ]

    # =====================================================
    # ERROR BUILDING
    # =====================================================

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

    # =====================================================
    # MAIN VALIDATION ENTRY
    # =====================================================

    def validate_trunk_operation(
        self,
        intent_type,
        parameters,
        step_number
    ):

        errors = []

        # -------------------------------------------------
        # Allowed VLAN validation
        # -------------------------------------------------

        if intent_type == "configure_allowed_vlans":

            errors.extend(

                self.validate_allowed_vlans(
                    parameters=parameters,
                    step_number=step_number
                )
            )

        # -------------------------------------------------
        # Native VLAN validation
        # -------------------------------------------------

        elif intent_type == "set_native_vlan":

            errors.extend(

                self.validate_native_vlan(
                    parameters=parameters,
                    step_number=step_number
                )
            )

        # -------------------------------------------------
        # Trunk mode validation
        # -------------------------------------------------

        elif intent_type == "set_interface_mode_trunk":

            errors.extend(

                self.validate_trunk_mode(
                    parameters=parameters,
                    step_number=step_number
                )
            )

        return errors

    # =====================================================
    # TRUNK MODE VALIDATION
    # =====================================================

    def validate_trunk_mode(
        self,
        parameters,
        step_number
    ):

        """
        Basic trunk mode validation
        """

        errors = []

        interface = parameters.get(
            "interface"
        )

        # ---------------------------------------------
        # interface required
        # ---------------------------------------------

        if interface is None:

            errors.append(

                self.build_error(
                    error_type="missing_interface",
                    step=step_number,
                    parameter="interface",
                    message=(
                        "interface required "
                        "for trunk configuration"
                    )
                )
            )

        return errors

    # =====================================================
    # ALLOWED VLAN VALIDATION
    # =====================================================

    def validate_allowed_vlans(
        self,
        parameters,
        step_number
    ):

        errors = []

        allowed_vlans = parameters.get(
            "allowed_vlans"
        )

        # ---------------------------------------------
        # Must be list
        # ---------------------------------------------

        if not isinstance(
            allowed_vlans,
            list
        ):

            errors.append(

                self.build_error(
                    error_type="invalid_allowed_vlans",
                    step=step_number,
                    parameter="allowed_vlans",
                    message=(
                        "allowed_vlans "
                        "must be list"
                    )
                )
            )

            return errors

        # ---------------------------------------------
        # Empty list check
        # ---------------------------------------------

        if len(allowed_vlans) == 0:

            errors.append(

                self.build_error(
                    error_type="empty_allowed_vlans",
                    step=step_number,
                    parameter="allowed_vlans",
                    message=(
                        "allowed_vlans "
                        "cannot be empty"
                    )
                )
            )

        # ---------------------------------------------
        # Validate each VLAN
        # ---------------------------------------------

        seen = set()

        for vlan in allowed_vlans:

            # Integer validation

            if not isinstance(
                vlan,
                int
            ):

                errors.append(

                    self.build_error(
                        error_type="invalid_allowed_vlan",
                        step=step_number,
                        parameter="allowed_vlans",
                        message=(
                            "allowed_vlans "
                            "must contain integers"
                        )
                    )
                )

                continue

            # Range validation

            if vlan < self.VLAN_MIN:

                errors.append(

                    self.build_error(
                        error_type="invalid_vlan_range",
                        step=step_number,
                        parameter="allowed_vlans",
                        message=(
                            f"VLAN {vlan} "
                            f"below valid range"
                        )
                    )
                )

            if vlan > self.VLAN_MAX:

                errors.append(

                    self.build_error(
                        error_type="invalid_vlan_range",
                        step=step_number,
                        parameter="allowed_vlans",
                        message=(
                            f"VLAN {vlan} "
                            f"exceeds valid range"
                        )
                    )
                )

            # Duplicate VLAN detection

            if vlan in seen:

                errors.append(

                    self.build_error(
                        error_type="duplicate_vlan",
                        step=step_number,
                        parameter="allowed_vlans",
                        message=(
                            f"Duplicate VLAN "
                            f"{vlan} detected"
                        )
                    )
                )

            seen.add(vlan)

        return errors

    # =====================================================
    # NATIVE VLAN VALIDATION
    # =====================================================

    def validate_native_vlan(
        self,
        parameters,
        step_number
    ):

        errors = []

        native_vlan = parameters.get(
            "native_vlan"
        )

        # ---------------------------------------------
        # Integer validation
        # ---------------------------------------------

        if not isinstance(
            native_vlan,
            int
        ):

            errors.append(

                self.build_error(
                    error_type="invalid_native_vlan",
                    step=step_number,
                    parameter="native_vlan",
                    message=(
                        "native_vlan "
                        "must be integer"
                    )
                )
            )

            return errors

        # ---------------------------------------------
        # Range validation
        # ---------------------------------------------

        if native_vlan < self.VLAN_MIN:

            errors.append(

                self.build_error(
                    error_type="invalid_native_vlan",
                    step=step_number,
                    parameter="native_vlan",
                    message=(
                        "native_vlan "
                        "below valid range"
                    )
                )
            )

        if native_vlan > self.VLAN_MAX:

            errors.append(

                self.build_error(
                    error_type="invalid_native_vlan",
                    step=step_number,
                    parameter="native_vlan",
                    message=(
                        "native_vlan "
                        "exceeds valid range"
                    )
                )
            )

        # ---------------------------------------------
        # Reserved VLAN warning
        # ---------------------------------------------

        if native_vlan in self.RESERVED_VLANS:

            errors.append(

                self.build_error(
                    error_type="reserved_native_vlan",
                    step=step_number,
                    parameter="native_vlan",
                    message=(
                        "reserved VLAN "
                        "should not be used "
                        "as native VLAN"
                    )
                )
            )

        return errors