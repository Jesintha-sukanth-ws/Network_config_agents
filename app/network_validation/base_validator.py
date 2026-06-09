"""
Base Validator

Shared validation utilities.

Contains:
- standard error generation
- reusable validation helpers

Does NOT contain:
- VLAN rules
- Interface rules
- Policy values
"""

from typing import Dict, Any, Optional


class BaseValidator:


    @staticmethod
    def build_error(

        error_type: str,

        message: str,

        step: Optional[int] = None,

        parameter: Optional[str] = None,

        intent_type: Optional[str] = None,

        context: Optional[Dict[str, Any]] = None

    ) -> Dict:


        error = {

            "error_type":
            error_type,

            "message":
            message
        }


        if step is not None:

            error["step"] = step


        if parameter is not None:

            error["parameter"] = parameter


        if intent_type is not None:

            error["intent_type"] = intent_type


        if context:

            error["context"] = context


        return error


    @staticmethod
    def validate_required(

        value,

        parameter: str,

        step: int,

        context: Optional[Dict] = None

    ) -> list:


        if value is None:

            return [

                BaseValidator.build_error(

                    error_type=
                    "missing_parameter",

                    message=
                    f"{parameter} is required",

                    parameter=
                    parameter,

                    step=
                    step,

                    context=
                    context
                )
            ]


        return []


    @staticmethod
    def validate_type(

        value,

        expected_type,

        parameter: str,

        step: int,

        context: Optional[Dict] = None

    ) -> list:


        if not isinstance(
            value,
            expected_type
        ):

            return [

                BaseValidator.build_error(

                    error_type=
                    "invalid_type",

                    message=
                    f"{parameter} "
                    f"must be "
                    f"{expected_type.__name__}",

                    parameter=
                    parameter,

                    step=
                    step,

                    context=
                    context
                )
            ]


        return []