# Workflow Validator
"""
Workflow Validator

Final orchestration validation layer.

Responsibilities:
- Aggregate all validator layers
- Execute VLAN validation
- Execute interface validation
- Execute trunk validation
- Return unified validation response

This validator DOES NOT:
- connect to devices
- validate runtime operational state
- validate telemetry
- execute configurations

Validation Pipeline:

LLM Output
    ↓
Schema Validator
    ↓
Workflow Validator
    ├── VLAN Validator
    ├── Interface Validator
    └── Trunk Validator
    ↓
Execution Engine
"""


from app.network_validation.vlan_validator import (
    VlanValidator
)

from app.network_validation.interface_validator import (
    InterfaceValidator
)

from app.network_validation.trunk_validator import (
    TrunkValidator
)


class WorkflowValidator:

    """
    Final orchestration validator
    """

    # =====================================================
    # VLAN RELATED INTENTS
    # =====================================================

    VLAN_INTENTS = [

        "create_vlan",

        "delete_vlan",

        "rename_vlan",

        "assign_access_vlan"
    ]

    # =====================================================
    # INTERFACE RELATED INTENTS
    # =====================================================

    INTERFACE_INTENTS = [

        "set_interface_mode_access",

        "assign_access_vlan",

        "configure_interface_description",

        "shutdown_interface",

        "enable_interface",

        "configure_speed",

        "configure_duplex"
    ]

    # =====================================================
    # TRUNK RELATED INTENTS
    # =====================================================

    TRUNK_INTENTS = [

        "set_interface_mode_trunk",

        "configure_allowed_vlans",

        "set_native_vlan"
    ]

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self):

        self.vlan_validator = (
            VlanValidator()
        )

        self.interface_validator = (
            InterfaceValidator()
        )

        self.trunk_validator = (
            TrunkValidator()
        )

    # =====================================================
    # ERROR BUILDING
    # =====================================================

    def build_error(
        self,
        error_type: str,
        message: str,
        step: int = None,
        intent_type: str = None,
        parameter: str = None
    ) -> dict:
        """
        Build a standardized error dictionary.
        """
        error = {
            "error_type": error_type,
            "message": message
        }
        
        if step is not None:
            error["step"] = step
        if intent_type:
            error["intent_type"] = intent_type
        if parameter:
            error["parameter"] = parameter
            
        return error

    def validate_workflow(
        self,
        workflow
    ):

        """
        Validate complete orchestration workflow
        """

        errors = []

        # -------------------------------------------------
        # Workflow must be list
        # -------------------------------------------------

        if not isinstance(
            workflow,
            list
        ):

            return {

                "safe": False,

                "errors": [

                    self.build_error(
                        error_type="invalid_workflow",
                        message=(
                            "workflow must be list"
                        )
                    )
                ]
            }

        # -------------------------------------------------
        # Validate each step
        # -------------------------------------------------

        for index, step in enumerate(workflow):

            step_number = index + 1

            # =============================================
            # Step must be dictionary
            # =============================================

            if not isinstance(
                step,
                dict
            ):

                errors.append(

                    self.build_error(
                        error_type="invalid_step",
                        step=step_number,
                        message=(
                            "workflow step "
                            "must be dictionary"
                        )
                    )
                )

                continue

            intent_type = step.get(
                "intent_type"
            )

            parameters = step.get(
                "parameters",
                {}
            )

            # =============================================
            # intent_type required
            # =============================================

            if not intent_type:

                errors.append(

                    self.build_error(
                        error_type="missing_intent_type",
                        step=step_number,
                        message=(
                            "intent_type missing"
                        )
                    )
                )

                continue

            # =============================================
            # parameters must be dictionary
            # =============================================

            if not isinstance(
                parameters,
                dict
            ):

                errors.append(

                    self.build_error(
                        error_type="invalid_parameters",
                        step=step_number,
                        intent_type=intent_type,
                        message=(
                            "parameters must "
                            "be dictionary"
                        )
                    )
                )

                continue

            # =============================================
            # VLAN VALIDATION
            # =============================================

            if intent_type in self.VLAN_INTENTS:

                vlan_errors = (

                    self.vlan_validator
                    .validate_vlan_operation(

                        intent_type=intent_type,

                        parameters=parameters,

                        step_number=step_number
                    )
                )

                errors.extend(
                    vlan_errors
                )

            # =============================================
            # INTERFACE VALIDATION
            # =============================================

            if intent_type in self.INTERFACE_INTENTS:

                interface_errors = (

                    self.interface_validator
                    .validate_interface_operation(

                        intent_type=intent_type,

                        parameters=parameters,

                        step_number=step_number
                    )
                )

                errors.extend(
                    interface_errors
                )

            # =============================================
            # TRUNK VALIDATION
            # =============================================

            if intent_type in self.TRUNK_INTENTS:

                trunk_errors = (

                    self.trunk_validator
                    .validate_trunk_operation(

                        intent_type=intent_type,

                        parameters=parameters,

                        step_number=step_number
                    )
                )

                errors.extend(
                    trunk_errors
                )

        # =================================================
        # FINAL RESULT
        # =================================================

        return {

            "safe": len(errors) == 0,

            "errors": errors
        }