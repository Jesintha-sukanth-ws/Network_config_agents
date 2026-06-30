from app.network_validation.vlan_validator import VlanValidator
from app.network_validation.interface_validator import InterfaceValidator


class WorkflowValidator:

    def __init__(self):

        self.validators = [VlanValidator(),InterfaceValidator()]


    def validate_workflow(self,workflow: list) -> dict:
        errors=[]

        for index,step in enumerate(workflow,start=1):
            intent_type=step.get("intent_type")
            params=step.get("parameters",{})

            for validator in self.validators:

                if validator.can_handle(
                    intent_type
                ):

                    errors.extend( validator.validate(
                            intent_type,
                            params,
                            index
                        )
                    )



        return {

            "safe":len(errors)==0,

            "errors":errors
        }