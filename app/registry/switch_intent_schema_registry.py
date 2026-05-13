"""
Switch Intent Schema Registry

Single source of truth for:
- supported intents
- parameter contracts
- aliases
- parameter datatypes
"""

SWITCH_INTENT_SCHEMAS = {

    # =====================================================
    # VLAN
    # =====================================================

    "create_vlan": {

        "description": "Create VLAN on switch",

        "required_parameters": [
            "vlan_id"
        ],

        "optional_parameters": [
            "name"
        ],

        "parameter_types": {
            "vlan_id": int,
            "name": str
        },

        "aliases": [
            "add_vlan",
            "new_vlan"
        ]
    },

    "delete_vlan": {

        "description": "Delete VLAN from switch",

        "required_parameters": [
            "vlan_id"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "vlan_id": int
        },

        "aliases": [
            "remove_vlan"
        ]
    },

    "rename_vlan": {

        "description": "Rename VLAN",

        "required_parameters": [
            "vlan_id",
            "name"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "vlan_id": int,
            "name": str
        },

        "aliases": [
            "set_vlan_name"
        ]
    },

    # =====================================================
    # INTERFACE VLAN
    # =====================================================

    "set_interface_mode_access": {

        "description": "Configure access mode",

        "required_parameters": [
            "interface"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "interface": str
        },

        "aliases": [
            "access_port"
        ]
    },

    "assign_access_vlan": {

        "description": "Assign VLAN to interface",

        "required_parameters": [
            "interface",
            "vlan_id"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "interface": str,
            "vlan_id": int
        },

        "aliases": [
            "assign_vlan"
        ]
    },

    "set_interface_mode_trunk": {

        "description": "Configure trunk mode",

        "required_parameters": [
            "interface"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "interface": str
        },

        "aliases": [
            "enable_trunk"
        ]
    },

    "configure_allowed_vlans": {

        "description": "Configure allowed VLANs",

        "required_parameters": [
            "interface",
            "allowed_vlans"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "interface": str,
            "allowed_vlans": list
        },

        "aliases": []
    },

    "set_native_vlan": {

        "description": "Configure native VLAN",

        "required_parameters": [
            "interface",
            "native_vlan"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "interface": str,
            "native_vlan": int
        },

        "aliases": []
    },

    # =====================================================
    # INTERFACE
    # =====================================================

    "configure_interface_description": {

        "description": "Configure interface description",

        "required_parameters": [
            "interface",
            "description"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "interface": str,
            "description": str
        },

        "aliases": []
    },

    "shutdown_interface": {

        "description": "Shutdown interface",

        "required_parameters": [
            "interface"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "interface": str
        },

        "aliases": [
            "disable_port"
        ]
    },

    "enable_interface": {

        "description": "Enable interface",

        "required_parameters": [
            "interface"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "interface": str
        },

        "aliases": [
            "no_shutdown"
        ]
    },

    "configure_speed": {

        "description": "Configure interface speed",

        "required_parameters": [
            "interface",
            "speed"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "interface": str,
            "speed": (int, str)
        },

        "aliases": []
    },

    "configure_duplex": {

        "description": "Configure interface duplex",

        "required_parameters": [
            "interface",
            "duplex"
        ],

        "optional_parameters": [],

        "parameter_types": {
            "interface": str,
            "duplex": str
        },

        "aliases": []
    },

    # =====================================================
    # SYSTEM
    # =====================================================

    "save_configuration": {

        "description": "Save running configuration",

        "required_parameters": [],

        "optional_parameters": [],

        "parameter_types": {},

        "aliases": [
            "write_memory"
        ]
    }
}