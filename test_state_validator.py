"""
State Validator Test
"""

import json

from app.network_validation.state_validator import (
    StateValidator
)


validator = StateValidator()

# =====================================================
# CURRENT DEVICE STATE
# =====================================================

current_state = {

    "vlans": {

        "10": {
            "name": "FINANCE"
        },

        "20": {
            "name": "HR"
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

# =====================================================
# WORKFLOW
# =====================================================

workflow = [

    {
        "intent_type": "create_vlan",

        "parameters": {
            "vlan_id": 10
        }
    },

    {
        "intent_type": "create_vlan",

        "parameters": {
            "vlan_id": 30
        }
    },

    {
        "intent_type": "assign_access_vlan",

        "parameters": {
            "interface": "Gi1/0/5",
            "vlan_id": 10
        }
    },

    {
        "intent_type": "set_interface_mode_trunk",

        "parameters": {
            "interface": "Gi1/0/48"
        }
    },

    {
        "intent_type": "configure_allowed_vlans",

        "parameters": {
            "interface": "Gi1/0/48",
            "allowed_vlans": [10, 20]
        }
    },

    {
        "intent_type": "set_native_vlan",

        "parameters": {
            "interface": "Gi1/0/48",
            "native_vlan": 99
        }
    },

    {
        "intent_type": "configure_interface_description",

        "parameters": {
            "interface": "Gi1/0/5",
            "description": "Finance Port"
        }
    },

    {
        "intent_type": "shutdown_interface",

        "parameters": {
            "interface": "Gi1/0/5"
        }
    }
]

# =====================================================
# RUN VALIDATION
# =====================================================

result = validator.validate_state(
    workflow,
    current_state
)

print(
    json.dumps(
        result,
        indent=2
    )
)