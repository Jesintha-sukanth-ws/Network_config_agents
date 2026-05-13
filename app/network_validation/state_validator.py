"""
State Validator

Compares desired workflow against current device state.

Purpose:
- prevent unnecessary execution
- provide idempotent orchestration
- detect already-configured state
- detect missing dependencies

This validator DOES NOT:
- connect to devices
- execute configuration
- validate runtime metrics

Expected current_state structure:

{
    "vlans": {
        "10": {
            "name": "FINANCE"
        }
    },

    "interfaces": {

        "Gi1/0/5": {

            "mode": "access",

            "access_vlan": 10,

            "shutdown": False,

            "description": "Finance Port"
        },

        "Gi1/0/48": {

            "mode": "trunk",

            "allowed_vlans": [10, 20],

            "native_vlan": 99
        }
    }
}
"""

class StateValidator:

    """
    Device state validation engine
    """

    # =====================================================
    # STANDARD STATE RESULT
    # =====================================================

    def build_state_result(
        self,
        execute,
        reason=None,
        errors=None
    ):

        return {

            "execute": execute,

            "reason": reason,

            "errors": errors or []
        }

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

    def build_result(
        self,
        safe: bool,
        errors: list = None,
        extra_data: dict = None
    ) -> dict:
        """
        Build a standardized validation result.
        """
        result = {
            "safe": safe,
            "errors": errors or []
        }
        
        if extra_data:
            result.update(extra_data)
            
        return result

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def validate_state(
        self,
        workflow,
        current_state
    ):

        """
        Validate workflow against current device state
        """

        errors = []

        execution_plan = []

        vlans = current_state.get(
            "vlans",
            {}
        )

        interfaces = current_state.get(
            "interfaces",
            {}
        )

        # -------------------------------------------------
        # Process workflow steps
        # -------------------------------------------------

        for index, step in enumerate(workflow):

            step_number = index + 1

            intent_type = step.get(
                "intent_type"
            )

            parameters = step.get(
                "parameters",
                {}
            )

            # =============================================
            # VLAN OPERATIONS
            # =============================================

            if intent_type == "create_vlan":

                result = self.validate_create_vlan(
                    step_number,
                    parameters,
                    vlans
                )

            elif intent_type == "delete_vlan":

                result = self.validate_delete_vlan(
                    step_number,
                    parameters,
                    vlans
                )

            elif intent_type == "rename_vlan":

                result = self.validate_rename_vlan(
                    step_number,
                    parameters,
                    vlans
                )

            # =============================================
            # ACCESS VLAN
            # =============================================

            elif intent_type == "assign_access_vlan":

                result = self.validate_access_vlan_assignment(
                    step_number,
                    parameters,
                    interfaces,
                    vlans
                )

            # =============================================
            # ACCESS MODE
            # =============================================

            elif intent_type == "set_interface_mode_access":

                result = self.validate_access_mode(
                    step_number,
                    parameters,
                    interfaces
                )

            # =============================================
            # TRUNK MODE
            # =============================================

            elif intent_type == "set_interface_mode_trunk":

                result = self.validate_trunk_mode(
                    step_number,
                    parameters,
                    interfaces
                )

            # =============================================
            # ALLOWED VLANS
            # =============================================

            elif intent_type == "configure_allowed_vlans":

                result = self.validate_allowed_vlans(
                    step_number,
                    parameters,
                    interfaces
                )

            # =============================================
            # NATIVE VLAN
            # =============================================

            elif intent_type == "set_native_vlan":

                result = self.validate_native_vlan(
                    step_number,
                    parameters,
                    interfaces
                )

            # =============================================
            # DESCRIPTION
            # =============================================

            elif (
                intent_type
                ==
                "configure_interface_description"
            ):

                result = self.validate_description(
                    step_number,
                    parameters,
                    interfaces
                )

            # =============================================
            # SHUTDOWN
            # =============================================

            elif intent_type == "shutdown_interface":

                result = self.validate_shutdown(
                    step_number,
                    parameters,
                    interfaces
                )

            # =============================================
            # ENABLE
            # =============================================

            elif intent_type == "enable_interface":

                result = self.validate_enable(
                    step_number,
                    parameters,
                    interfaces
                )

            else:

                result = self.build_state_result(
                    execute=True
                )

            # =============================================
            # Aggregate
            # =============================================

            errors.extend(
                result.get(
                    "errors",
                    []
                )
            )

            execution_plan.append({

                "step": step_number,

                "intent_type": intent_type,

                "execute": result.get(
                    "execute",
                    True
                ),

                "reason": result.get(
                    "reason"
                )
            })

        # -------------------------------------------------
        # Final Result
        # -------------------------------------------------

        return self.build_result(

            safe=len(errors) == 0,

            errors=errors,

            extra_data={

                "execution_plan": execution_plan
            }
        )

    # =====================================================
    # CREATE VLAN
    # =====================================================

    def validate_create_vlan(
        self,
        step_number,
        parameters,
        vlans
    ):

        vlan_id = parameters.get(
            "vlan_id"
        )

        vlan_exists = (
            str(vlan_id)
            in
            vlans
        )

        if vlan_exists:

            return self.build_state_result(

                execute=False,

                reason=(
                    f"VLAN {vlan_id} "
                    f"already exists"
                )
            )

        return self.build_state_result(
            execute=True
        )

    # =====================================================
    # DELETE VLAN
    # =====================================================

    def validate_delete_vlan(
        self,
        step_number,
        parameters,
        vlans
    ):

        vlan_id = parameters.get(
            "vlan_id"
        )

        vlan_exists = (
            str(vlan_id)
            in
            vlans
        )

        if not vlan_exists:

            return self.build_state_result(

                execute=False,

                reason=(
                    f"VLAN {vlan_id} "
                    f"does not exist"
                )
            )

        return self.build_state_result(
            execute=True
        )

    # =====================================================
    # RENAME VLAN
    # =====================================================

    def validate_rename_vlan(
        self,
        step_number,
        parameters,
        vlans
    ):

        vlan_id = parameters.get(
            "vlan_id"
        )

        new_name = parameters.get(
            "name"
        )

        vlan = vlans.get(
            str(vlan_id)
        )

        if not vlan:

            return self.build_state_result(

                execute=False,

                reason=(
                    f"VLAN {vlan_id} "
                    f"does not exist"
                )
            )

        current_name = vlan.get(
            "name"
        )

        if current_name == new_name:

            return self.build_state_result(

                execute=False,

                reason=(
                    "VLAN already has "
                    "same name"
                )
            )

        return self.build_state_result(
            execute=True
        )

    # =====================================================
    # ACCESS MODE
    # =====================================================

    def validate_access_mode(
        self,
        step_number,
        parameters,
        interfaces
    ):

        interface = parameters.get(
            "interface"
        )

        current = interfaces.get(
            interface,
            {}
        )

        if current.get("mode") == "access":

            return self.build_state_result(

                execute=False,

                reason=(
                    f"{interface} already "
                    f"in access mode"
                )
            )

        return self.build_state_result(
            execute=True
        )

    # =====================================================
    # ACCESS VLAN
    # =====================================================

    def validate_access_vlan_assignment(
        self,
        step_number,
        parameters,
        interfaces,
        vlans
    ):

        vlan_id = parameters.get(
            "vlan_id"
        )

        interface = parameters.get(
            "interface"
        )

        # VLAN must exist

        if str(vlan_id) not in vlans:

            return self.build_state_result(

                execute=False,

                errors=[

                    self.build_error(
                        error_type="missing_vlan",
                        step=step_number,
                        intent_type="assign_access_vlan",
                        parameter="vlan_id",
                        message=(
                            f"VLAN {vlan_id} "
                            f"does not exist"
                        )
                    )
                ]
            )

        current = interfaces.get(
            interface,
            {}
        )

        if current.get("access_vlan") == vlan_id:

            return self.build_state_result(

                execute=False,

                reason=(
                    f"{interface} already "
                    f"assigned to VLAN {vlan_id}"
                )
            )

        return self.build_state_result(
            execute=True
        )

    # =====================================================
    # TRUNK MODE
    # =====================================================

    def validate_trunk_mode(
        self,
        step_number,
        parameters,
        interfaces
    ):

        interface = parameters.get(
            "interface"
        )

        current = interfaces.get(
            interface,
            {}
        )

        if current.get("mode") == "trunk":

            return self.build_state_result(

                execute=False,

                reason=(
                    f"{interface} already "
                    f"in trunk mode"
                )
            )

        return self.build_state_result(
            execute=True
        )

    # =====================================================
    # ALLOWED VLANS
    # =====================================================

    def validate_allowed_vlans(
        self,
        step_number,
        parameters,
        interfaces
    ):

        interface = parameters.get(
            "interface"
        )

        new_vlans = parameters.get(
            "allowed_vlans"
        )

        current = interfaces.get(
            interface,
            {}
        )

        current_vlans = current.get(
            "allowed_vlans",
            []
        )

        if sorted(current_vlans) == sorted(new_vlans):

            return self.build_state_result(

                execute=False,

                reason=(
                    "allowed VLANs already "
                    "configured"
                )
            )

        return self.build_state_result(
            execute=True
        )

    # =====================================================
    # NATIVE VLAN
    # =====================================================

    def validate_native_vlan(
        self,
        step_number,
        parameters,
        interfaces
    ):

        interface = parameters.get(
            "interface"
        )

        native_vlan = parameters.get(
            "native_vlan"
        )

        current = interfaces.get(
            interface,
            {}
        )

        if current.get("native_vlan") == native_vlan:

            return self.build_state_result(

                execute=False,

                reason=(
                    "native VLAN already "
                    "configured"
                )
            )

        return self.build_state_result(
            execute=True
        )

    # =====================================================
    # DESCRIPTION
    # =====================================================

    def validate_description(
        self,
        step_number,
        parameters,
        interfaces
    ):

        interface = parameters.get(
            "interface"
        )

        description = parameters.get(
            "description"
        )

        current = interfaces.get(
            interface,
            {}
        )

        if current.get("description") == description:

            return self.build_state_result(

                execute=False,

                reason=(
                    "description already "
                    "configured"
                )
            )

        return self.build_state_result(
            execute=True
        )

    # =====================================================
    # SHUTDOWN
    # =====================================================

    def validate_shutdown(
        self,
        step_number,
        parameters,
        interfaces
    ):

        interface = parameters.get(
            "interface"
        )

        current = interfaces.get(
            interface,
            {}
        )

        if current.get("shutdown") is True:

            return self.build_state_result(

                execute=False,

                reason=(
                    f"{interface} already shutdown"
                )
            )

        return self.build_state_result(
            execute=True
        )

    # =====================================================
    # ENABLE
    # =====================================================

    def validate_enable(
        self,
        step_number,
        parameters,
        interfaces
    ):

        interface = parameters.get(
            "interface"
        )

        current = interfaces.get(
            interface,
            {}
        )

        if current.get("shutdown") is False:

            return self.build_state_result(

                execute=False,

                reason=(
                    f"{interface} already enabled"
                )
            )

        return self.build_state_result(
            execute=True
        )