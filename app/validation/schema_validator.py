"""
Schema Validation - Validates workflow structure
against switch intent schema registry.
"""

from app.registry.switch_intent_schema_registry import (
    SWITCH_INTENT_SCHEMAS
)


class SchemaValidator:
    """
    Registry-driven schema validator.

    Responsibilities:
    - Validate workflow structure
    - Resolve aliases
    - Validate supported intents
    - Validate required parameters
    - Reject unknown parameters
    - Validate parameter datatypes

    Does NOT perform:
    - VLAN range validation
    - Interface existence validation
    - Device capability validation
    - Workflow dependency validation
    """

    def validate_workflow(
        self,
        workflow_json
    ):

        errors = []

        normalized_workflow = []

        # ==========================================
        # Validate top-level workflow structure
        # ==========================================

        if not isinstance(workflow_json, dict):

            return {
                "safe": False,
                "errors": [
                    self._build_error(
                        error_type="invalid_structure",
                        message="Workflow payload must be a dictionary"
                    )
                ],
                "workflow": []
            }

        workflow = workflow_json.get("workflow")

        if workflow is None:

            return {
                "safe": False,
                "errors": [
                    self._build_error(
                        error_type="missing_workflow",
                        message="Missing workflow field"
                    )
                ],
                "workflow": []
            }

        if not isinstance(workflow, list):

            return {
                "safe": False,
                "errors": [
                    self._build_error(
                        error_type="invalid_workflow_type",
                        message="Workflow must be a list"
                    )
                ],
                "workflow": []
            }

        # ==========================================
        # Validate each workflow step
        # ==========================================

        for index, step in enumerate(workflow):

            step_number = index + 1

            # --------------------------------------
            # Step must be dictionary
            # --------------------------------------

            if not isinstance(step, dict):

                errors.append(
                    self._build_error(
                        error_type="invalid_step",
                        step=step_number,
                        message="Workflow step must be a dictionary"
                    )
                )

                continue

            # --------------------------------------
            # Extract fields
            # --------------------------------------

            intent_type = step.get("intent_type")

            parameters = step.get(
                "parameters",
                {}
            )

            # --------------------------------------
            # intent_type required
            # --------------------------------------

            if not intent_type:

                errors.append(
                    self._build_error(
                        error_type="missing_intent_type",
                        step=step_number,
                        message="Missing intent_type"
                    )
                )

                continue

            # --------------------------------------
            # Resolve aliases
            # --------------------------------------

            intent_type = self.resolve_alias(
                intent_type
            )

            # --------------------------------------
            # Validate supported intent
            # --------------------------------------

            if intent_type not in SWITCH_INTENT_SCHEMAS:

                errors.append(
                    self._build_error(
                        error_type="unsupported_intent",
                        step=step_number,
                        intent_type=intent_type,
                        message=f"Unsupported intent: {intent_type}"
                    )
                )

                continue

            # --------------------------------------
            # Parameters must be dictionary
            # --------------------------------------

            if not isinstance(parameters, dict):

                errors.append(
                    self._build_error(
                        error_type="invalid_parameters",
                        step=step_number,
                        intent_type=intent_type,
                        message="Parameters must be a dictionary"
                    )
                )

                continue

            schema = SWITCH_INTENT_SCHEMAS[
                intent_type
            ]

            required_parameters = schema.get(
                "required_parameters",
                []
            )

            optional_parameters = schema.get(
                "optional_parameters",
                []
            )

            parameter_types = schema.get(
                "parameter_types",
                {}
            )

            allowed_parameters = (
                required_parameters
                +
                optional_parameters
            )

            # --------------------------------------
            # Validate required parameters
            # --------------------------------------

            for required_param in required_parameters:

                if required_param not in parameters:

                    errors.append(
                        self._build_error(
                            error_type="missing_parameter",
                            step=step_number,
                            intent_type=intent_type,
                            parameter=required_param,
                            message=(
                                f"Missing required parameter: "
                                f"{required_param}"
                            )
                        )
                    )

            # --------------------------------------
            # Reject unknown parameters
            # --------------------------------------

            for param_name in parameters.keys():

                if param_name not in allowed_parameters:

                    errors.append(
                        self._build_error(
                            error_type="unknown_parameter",
                            step=step_number,
                            intent_type=intent_type,
                            parameter=param_name,
                            message=(
                                f"Unknown parameter: "
                                f"{param_name}"
                            )
                        )
                    )

            # --------------------------------------
            # Validate parameter datatypes
            # --------------------------------------

            for param_name, param_value in parameters.items():

                expected_type = parameter_types.get(
                    param_name
                )

                if expected_type:

                    if not isinstance(
                        param_value,
                        expected_type
                    ):

                        errors.append(
                            self._build_error(
                                error_type="invalid_parameter_type",
                                step=step_number,
                                intent_type=intent_type,
                                parameter=param_name,
                                message=(
                                    f"Parameter '{param_name}' "
                                    f"must be "
                                    f"{expected_type.__name__}"
                                )
                            )
                        )

            # --------------------------------------
            # Add normalized workflow step
            # --------------------------------------

            normalized_workflow.append({

                "intent_type": intent_type,

                "parameters": parameters

            })

        # ==========================================
        # Final Result
        # ==========================================

        return {

            "safe": len(errors) == 0,

            "errors": errors,

            "workflow": normalized_workflow
        }

    # ==================================================
    # Alias Resolution
    # ==================================================

    def resolve_alias(
        self,
        intent_type
    ):

        # Direct match
        if intent_type in SWITCH_INTENT_SCHEMAS:
            return intent_type

        # Alias lookup
        for canonical_intent, schema in SWITCH_INTENT_SCHEMAS.items():

            aliases = schema.get(
                "aliases",
                []
            )

            if intent_type in aliases:
                return canonical_intent

        return intent_type

    # ==================================================
    # Standard Error Format
    # ==================================================

    def _build_error(
        self,
        error_type,
        message,
        step=None,
        intent_type=None,
        parameter=None
    ):

        return {

            "error_type": error_type,

            "step": step,

            "intent_type": intent_type,

            "parameter": parameter,

            "message": message
        }