# Knowledge Base Article: Interface Configuration Workflows

**Article ID:** kb-network-002  
**Domain:** interface  
**Version:** 1.0  
**Chroma Metadata:**
```json
{
  "domain": "interface",
  "article_id": "kb-network-002",
  "intent_types": ["configure_access_port", "configure_trunk_port", "configure_interface_status"],
  "tags": ["interface", "port", "access", "trunk", "l2", "switching"]
}
```

---

## Overview

This article defines all supported interface configuration workflows for the network automation orchestrator. When the intent classifier routes a task to the `interface` domain, this article is retrieved and used to ground parameter extraction and payload generation.

Interface workflows configure physical and logical switchport behavior. All parameters extracted by the LLM must conform to the constraints defined per workflow below. The state validator checks live device state before any step is executed.

---

## Supported Intents

| Intent Type | Description | Trigger Examples |
|---|---|---|
| `configure_access_port` | Set a port to access mode with a single VLAN | "configure Gi0/1 as access port on vlan 10", "assign port to vlan 20" |
| `configure_trunk_port` | Set a port to trunk mode allowing multiple VLANs | "make Gi0/2 a trunk port", "configure trunk on interface Gi0/2 allow vlans 10,20" |
| `configure_interface_status` | Administratively bring an interface up or down | "shut down interface Gi0/1", "enable port Gi0/3", "no shutdown on Fa0/1" |

---

## Workflow: `configure_access_port`

### Purpose
Configures a switchport in access mode, assigning it to a single VLAN. Used for end-device connectivity (workstations, printers, IP phones).

### Required Parameters

| Parameter | Type | Constraint | Notes |
|---|---|---|---|
| `interface` | `str` | Must be a valid interface identifier | Examples: `GigabitEthernet0/1`, `Gi0/1`, `FastEthernet0/2`, `Fa0/2`, `Ethernet1` |
| `vlan_id` | `int` | 1–4094 | The VLAN the port will be placed in |

### Optional Parameters

| Parameter | Type | Constraint | Notes |
|---|---|---|---|
| `description` | `str` | Max 240 characters | Human-readable label for the interface |

### Validation Rules
- `interface` is required. If missing, the validator returns error type `missing_interface`.
- `vlan_id` must be an integer between 1 and 4094.
- Precondition: If `vlan_id` is not 1 (native), the VLAN must exist on the device. The state validator checks the VLAN table. If the VLAN does not exist, include a `create_vlan` step before this one.

### Dependencies
- If the target VLAN does not exist: `create_vlan` must precede this step.
- The dependency planner enforces this ordering automatically when both intents are present.

### Expected LLM Output
```json
{
  "workflow": [
    {
      "intent_type": "configure_access_port",
      "parameters": {
        "interface": "GigabitEthernet0/1",
        "vlan_id": 10,
        "description": "WORKSTATION-DESK-4B"
      }
    }
  ]
}
```

### SOP Notes
- **Cisco IOS / IOS-XE:**
  ```
  interface GigabitEthernet0/1
   switchport mode access
   switchport access vlan 10
   description WORKSTATION-DESK-4B
  ```
  Verify with `show interfaces GigabitEthernet0/1 switchport`.
- **Arista EOS:** Same syntax. Confirm with `show interfaces GigabitEthernet0/1 switchport`.
- **Cisco NX-OS:** Add `switchport` before mode configuration. Use `show interface GigabitEthernet0/1 switchport`.

---

## Workflow: `configure_trunk_port`

### Purpose
Configures a switchport in trunk mode to carry traffic for multiple VLANs. Used for uplinks between switches, router-on-a-stick interfaces, and server ports requiring multi-VLAN access.

### Required Parameters

| Parameter | Type | Constraint | Notes |
|---|---|---|---|
| `interface` | `str` | Must be a valid interface identifier | Examples: `GigabitEthernet0/2`, `Gi0/2` |

### Optional Parameters

| Parameter | Type | Constraint | Notes |
|---|---|---|---|
| `allowed_vlans` | `list[int]` | Each entry 1–4094 | VLANs permitted on the trunk. If omitted, all VLANs are allowed |
| `native_vlan` | `int` | 1–4094 | Untagged VLAN on the trunk. Defaults to VLAN 1 if not specified |
| `description` | `str` | Max 240 characters | Human-readable label for the interface |

### Validation Rules
- `interface` is required. If missing, the validator returns error type `missing_interface`.
- If `allowed_vlans` is provided, each entry must be an integer between 1 and 4094.
- If `native_vlan` is provided, it must be an integer between 1 and 4094.
- Precondition: All VLANs listed in `allowed_vlans` must exist on the device, or their creation must be included earlier in the workflow.

### Dependencies
- For each VLAN in `allowed_vlans` that does not yet exist: a `create_vlan` step must precede this step.
- The dependency planner resolves this automatically when both intents are present.

### Expected LLM Output
```json
{
  "workflow": [
    {
      "intent_type": "configure_trunk_port",
      "parameters": {
        "interface": "GigabitEthernet0/2",
        "allowed_vlans": [10, 20, 30],
        "native_vlan": 99,
        "description": "UPLINK-TO-CORE-SW01"
      }
    }
  ]
}
```

### SOP Notes
- **Cisco IOS / IOS-XE:**
  ```
  interface GigabitEthernet0/2
   switchport mode trunk
   switchport trunk allowed vlan 10,20,30
   switchport trunk native vlan 99
   description UPLINK-TO-CORE-SW01
  ```
  Verify with `show interfaces GigabitEthernet0/2 trunk`.
- **Arista EOS:** Same syntax. Confirm with `show interfaces GigabitEthernet0/2 trunk`.
- **Cisco NX-OS:** Prefix with `switchport`. Native VLAN is configured with `switchport trunk native vlan <id>`.

---

## Workflow: `configure_interface_status`

### Purpose
Administratively enables or disables an interface. Maps to `no shutdown` (up) or `shutdown` (down) in IOS terminology.

### Required Parameters

| Parameter | Type | Constraint | Canonical Values |
|---|---|---|---|
| `interface` | `str` | Must be a valid interface identifier | Examples: `GigabitEthernet0/1`, `Gi0/1` |
| `administrative_state` | `str` | Must be exactly `"up"` or `"down"` (uppercase also accepted, normalized to uppercase internally) | `"up"` / `"down"` |

### Optional Parameters
None.

### Canonical Value Mapping

The LLM must normalize user language into the canonical `administrative_state` values. Never return synonyms.

| User Says | Canonical Value |
|---|---|
| enable interface, bring up, no shutdown, activate, enable port | `"up"` |
| disable interface, shutdown, bring down, deactivate | `"down"` |

### Validation Rules
- `interface` is required. If missing, the validator returns error type `missing_interface`.
- `administrative_state` is required. Must be `"UP"` or `"DOWN"` after normalization. Any other value returns error type `invalid_state`.

### Dependencies
- None. `configure_interface_status` is a standalone step.
- If used in a multi-step workflow (e.g. shut down before reconfiguring), the dependency planner orders it appropriately.

### Expected LLM Output
```json
{
  "workflow": [
    {
      "intent_type": "configure_interface_status",
      "parameters": {
        "interface": "GigabitEthernet0/1",
        "administrative_state": "down"
      }
    }
  ]
}
```

### SOP Notes
- **Cisco IOS / IOS-XE:**
  - `administrative_state: down` → `shutdown`
  - `administrative_state: up` → `no shutdown`
  - Verify with `show interfaces GigabitEthernet0/1 status`.
- **Arista EOS:** Same syntax. Confirm with `show interfaces GigabitEthernet0/1`.
- **Cisco NX-OS:** Same syntax. Use `show interface GigabitEthernet0/1 brief`.

---

## Error Reference

These error types are produced by the interface validator and returned in the standard `{error_type, message, step, parameter}` format.

| Error Type | Trigger Condition |
|---|---|
| `missing_interface` | `interface` parameter is absent or empty |
| `unknown_intent` | `intent_type` is not in the supported set for this validator |
| `invalid_state` | `administrative_state` is not `"UP"` or `"DOWN"` |

---

## Multi-Step Example

A task that creates a VLAN, assigns an access port, and brings it up:

```json
{
  "workflow": [
    {
      "intent_type": "create_vlan",
      "parameters": {
        "vlan_id": 50,
        "name": "FINANCE"
      }
    },
    {
      "intent_type": "configure_access_port",
      "parameters": {
        "interface": "GigabitEthernet0/5",
        "vlan_id": 50,
        "description": "FINANCE-PC-01"
      }
    },
    {
      "intent_type": "configure_interface_status",
      "parameters": {
        "interface": "GigabitEthernet0/5",
        "administrative_state": "up"
      }
    }
  ]
}
```

The dependency planner will enforce correct ordering: VLAN creation before port assignment, port assignment before status change.
