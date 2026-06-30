# Knowledge Base Article: VLAN Configuration Workflows

**Article ID:** kb-network-001  
**Domain:** vlan  
**Version:** 1.0  
**Chroma Metadata:**
```json
{
  "domain": "vlan",
  "article_id": "kb-network-001",
  "intent_types": ["create_vlan", "delete_vlan"],
  "tags": ["vlan", "l2", "switching"]
}
```

---

## Overview

This article defines all supported VLAN configuration workflows for the network automation orchestrator. When the intent classifier routes a task to the `vlan` domain, this article is retrieved and used to ground parameter extraction and payload generation.

VLAN workflows operate at Layer 2 and are validated before any configuration is pushed to the device. All parameters extracted by the LLM must conform to the constraints defined per workflow below.

---

## Supported Intents

| Intent Type | Description | Trigger Examples |
|---|---|---|
| `create_vlan` | Create a new VLAN and optionally name it | "create vlan 10", "add vlan 20 named SERVERS", "provision vlan 100" |
| `delete_vlan` | Remove an existing VLAN from the device | "delete vlan 10", "remove vlan 30", "clean up vlan 50" |

---

## Workflow: `create_vlan`

### Purpose
Creates a VLAN entry in the device VLAN database. Optionally assigns a human-readable name.

### Required Parameters

| Parameter | Type | Constraint | Notes |
|---|---|---|---|
| `vlan_id` | `int` | 2–4094 | VLAN 1 is default and cannot be created. VLANs 1002–1005 are reserved on Cisco IOS |

### Optional Parameters

| Parameter | Type | Constraint | Notes |
|---|---|---|---|
| `name` | `str` | Max 32 characters, alphanumeric and underscores only | If omitted, device assigns default name (e.g. `VLAN0010`) |

### Validation Rules
- `vlan_id` must be an integer. Reject if string or float.
- `vlan_id` must be between 2 and 4094 inclusive.
- `vlan_id` must not be in the reserved range 1002–1005.
- If `name` is provided, it must not exceed 32 characters.
- If `name` is provided, it must match the pattern `[A-Za-z0-9_-]+` (no spaces or special characters).
- Precondition: VLAN must not already exist on the device. The state validator checks the live VLAN table before allowing execution.

### Dependencies
- None. `create_vlan` has no prerequisite workflow steps.

### Expected LLM Output
```json
{
  "workflow": [
    {
      "intent_type": "create_vlan",
      "parameters": {
        "vlan_id": 10,
        "name": "SERVERS"
      }
    }
  ]
}
```

### SOP Notes
- **Cisco IOS / IOS-XE:** Enter `vlan <id>` in global config mode, then `name <name>`. Verify with `show vlan brief`.
- **Arista EOS:** Same syntax. Confirm with `show vlan`.
- **Cisco NX-OS:** Use `vlan <id>` under config mode. NX-OS requires explicit `state active` for the VLAN to be operational.

---

## Workflow: `delete_vlan`

### Purpose
Removes an existing VLAN from the device VLAN database. Does not modify any port assignments — those must be cleaned up separately if required.

### Required Parameters

| Parameter | Type | Constraint | Notes |
|---|---|---|---|
| `vlan_id` | `int` | 2–4094 | VLAN 1 cannot be deleted (default VLAN protection) |

### Optional Parameters
None.

### Validation Rules
- `vlan_id` must be an integer.
- `vlan_id` must not be `1`. The validator enforces `default_vlan_protection` and will reject this with error type `default_vlan_protection`.
- `vlan_id` must not be in the reserved range 1002–1005.
- Precondition: VLAN must exist on the device. The state validator checks the live VLAN table before allowing deletion.

### Dependencies
- None. `delete_vlan` is a standalone step.
- If the task also includes port cleanup, those steps must be ordered before `delete_vlan` in the workflow.

### Expected LLM Output
```json
{
  "workflow": [
    {
      "intent_type": "delete_vlan",
      "parameters": {
        "vlan_id": 10
      }
    }
  ]
}
```

### SOP Notes
- **Cisco IOS / IOS-XE:** Use `no vlan <id>` in global config mode. Verify removal with `show vlan brief`.
- **Arista EOS:** Use `no vlan <id>`. Confirm with `show vlan`.
- **Cisco NX-OS:** Use `no vlan <id>`. Ports still assigned to the VLAN will fall back to VLAN 1.

---

## Error Reference

These error types are produced by the VLAN validator and returned in the standard `{error_type, message, step, field}` format.

| Error Type | Trigger Condition |
|---|---|
| `invalid_vlan_type` | `vlan_id` is not an integer |
| `invalid_vlan_range` | `vlan_id` is outside the allowed range |
| `default_vlan_protection` | Attempted delete of VLAN 1 |
| `reserved_vlan` | `vlan_id` falls in the reserved range 1002–1005 |
| `name_too_long` | `name` exceeds maximum character limit |
| `invalid_vlan_name` | `name` contains disallowed characters |

---

## Multi-Step Example

A task that provisions a VLAN before using it in a port assignment:

```json
{
  "workflow": [
    {
      "intent_type": "create_vlan",
      "parameters": {
        "vlan_id": 20,
        "name": "GUEST_WIFI"
      }
    },
    {
      "intent_type": "configure_access_port",
      "parameters": {
        "interface": "GigabitEthernet0/1",
        "vlan_id": 20
      }
    }
  ]
}
```

The dependency planner will enforce that `create_vlan` executes before `configure_access_port` when both are present in the same workflow.
