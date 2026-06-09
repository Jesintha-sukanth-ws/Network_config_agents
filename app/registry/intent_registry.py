CANONICAL_INTENT_SCHEMAS = {

    "create_vlan": {

        "description":
        "Provision a new VLAN.",

        "required_parameters":["vlan_id"],

        "optional_parameters":["name"],

        "parameter_types":{"vlan_id":int,"name":str},

        "aliases":["add_vlan","new_vlan","provision_vlan"],

        "rag_type":
        "create_vlan",

        "keywords":[

            "vlan",
            "create vlan",
            "add vlan",
            "vlan database"
        ],

        
        "requires": [],
        "provides": ["vlan_exists:{vlan_id}"],
        
        # SOP payload contract - authoritative output structure
        "sop_payload_contract": {
            "vlan_id": "",
            "vlan_name": ""
        }
    },


    "delete_vlan": {

        "description":
        "Remove an existing VLAN.",

        "required_parameters":[
            "vlan_id"
        ],

        "optional_parameters":[],

        "parameter_types":{

            "vlan_id":int
        },

        "aliases":[

            "remove_vlan",
            "drop_vlan",
            "purge_vlan"
        ],

        "rag_type":
        "delete_vlan",

        "keywords":[

            "delete vlan",
            "remove vlan",
            "no vlan"
        ],

        # Dependency metadata
        "requires": ["vlan_exists:{vlan_id}"],
        "provides": ["vlan_deleted:{vlan_id}"]
    },


    "configure_access_port": {

        "description":
        "Configure an interface as an access port.",

        "required_parameters":[

            "interface",
            "vlan_id"
        ],

        "optional_parameters":[
            "description"
        ],

        "parameter_types":{

            "interface":str,
            "vlan_id":int,
            "description":str
        },

        "aliases":[

            "set_access_port",
            "assign_vlan_to_port",
            "configure_host_port"
        ],

        "rag_type":
        "access_port",

        "keywords":[

            "access port",
            "switchport mode access",
            "access mode",
            "switchport access vlan"
        ],

        
        "requires": [
            "vlan_exists:{vlan_id}"
        ],
        "provides": [
            "interface_access_mode:{interface}",
            "interface_vlan_assigned:{interface}:{vlan_id}"
        ]
    },


    "configure_trunk_port": {

        "description":
        "Configure an interface as a trunk port.",

        "required_parameters":[

            "interface",
            "allowed_vlans"
        ],

        "optional_parameters":[

            "native_vlan",
            "description"
        ],

        "parameter_types":{

            "interface":str,
            "allowed_vlans":list,
            "native_vlan":int,
            "description":str
        },

        "aliases":[

            "set_trunk_port",
            "enable_trunking",
            "allow_vlans_on_trunk"
        ],

        "rag_type":
        "trunk_port",

        "keywords":[

            "trunk port",
            "switchport mode trunk",
            "trunk mode",
            "dot1q",
            "802.1q"
        ],

       
        "requires": [
            "vlans_exist:{allowed_vlans}"
        ],
        "provides": [
            "interface_trunk_mode:{interface}",
            "interface_trunk_vlans:{interface}:{allowed_vlans}"
        ]
    },


    "configure_interface_status": {

        "description":
        "Change administrative interface state (enable/disable, up/down, no shutdown/shutdown).",

        "required_parameters":[

            "interface",
            "administrative_state"
        ],

        "optional_parameters":[],

        "parameter_types":{

            "interface":str,
            "administrative_state":str
        },

        "aliases":[

            "shutdown_interface",
            "disable_port",
            "enable_port",
            "no_shutdown",
            "no_shutdown_interface",
            "bring_up_interface",
            "bring_down_interface",
            "activate_port",
            "deactivate_port",
            "enable_interface",
            "disable_interface"
        ],

        "rag_type":
        "interface_mode",

        "keywords":[

            "shutdown",
            "enable interface",
            "admin state",
            "port state",
            "no shutdown",
            "enable port",
            "disable port",
            "bring up",
            "bring down",
            "activate",
            "deactivate",
            "turn on port",
            "turn off port",
            "administratively enable",
            "administratively disable"
        ],

       
        "requires": [],
        
        "provides": [
            "interface_status:{interface}:{administrative_state}"
        ],
        
        # SOP payload contract - authoritative output structure
        "sop_payload_contract": {
            "interface": "",
            "administrative_state": ""
        }
    }

}



_ALIAS_MAP = {}


for canonical_key, schema in (CANONICAL_INTENT_SCHEMAS.items()):

    for alias in (schema.get("aliases",[])):
        normalized_alias=(alias.strip().lower().replace(" ","_"))
        _ALIAS_MAP[ normalized_alias]=canonical_key

def normalize_intent(intent:str)->str:
    return (intent.strip().lower().replace(" ","_"))

def get_canonical_intent(requested_intent:str)->str:
    normalized=(normalize_intent(requested_intent))
    if normalized in (CANONICAL_INTENT_SCHEMAS):
        return normalized
    return ( _ALIAS_MAP.get(normalized))


def get_intent_schema(canonical_key:str)->dict:
    return (CANONICAL_INTENT_SCHEMAS.get(canonical_key))