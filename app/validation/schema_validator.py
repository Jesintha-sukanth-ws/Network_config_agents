from app.registry.intent_registry import (CANONICAL_INTENT_SCHEMAS,get_canonical_intent)


class SchemaValidator:
    def validate_workflow(self,workflow_json):
        errors = []
        normalized_workflow = []
        workflow = workflow_json.get("workflow")

        if not workflow:
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

        for index, step in enumerate(workflow):

            step_number = index + 1

            if not isinstance(step, dict):

                errors.append(
                    self._build_error(
                        error_type="invalid_step",
                        step=step_number,
                        message="Workflow step must be a dictionary"
                    )
                )

                continue

            intent_type = step.get("intent_type")

            parameters = step.get(
                "parameters",
                {}
            )

            if not intent_type:

                errors.append(
                    self._build_error(
                        error_type="missing_intent_type",
                        step=step_number,
                        message="Missing intent_type"
                    )
                )

                continue
            canonical = get_canonical_intent(intent_type)

            if not canonical:

                errors.append(
                    self._build_error(
                        error_type="unsupported_intent",
                        step=step_number,
                        intent_type=intent_type,
                        message=f"Unsupported intent: {intent_type}"
                    )
                )

                continue

            intent_type = canonical

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

            schema = CANONICAL_INTENT_SCHEMAS[intent_type]

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

            # Reject unknown parameters
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

            # Validate parameter datatypes
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

            normalized_workflow.append({

                "intent_type": intent_type,

                "parameters": parameters

            })

        return {

            "safe": len(errors) == 0,

            "errors": errors,

            "workflow": normalized_workflow
        }

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
