# Analysis: interface_up Dependency for configure_access_port

## Current Behavior

**Intent:** `configure_access_port`

**Current Dependencies:**
```python
"requires": [
    "vlan_exists:{vlan_id}",
    "interface_up:{interface}"  # ← Under review
]
```

## Device Behavior Observation

**Observed:** A shutdown interface successfully accepted:
- `switchport mode access`
- `switchport access vlan X`

while remaining administratively down (`shutdown` state).

## Analysis

### Configuration vs. Operational Prerequisites

**Configuration Prerequisite:** A requirement that must be met for the device to accept the configuration command.

**Operational Prerequisite:** A requirement for the configuration to have its intended operational effect.

### Interface Status in IOS-XE

From `device_state_service.py` (lines 376-377):
```python
"status": "down" if shutdown else "up"
```

The `shutdown` state is an **administrative state**, not a configuration blocker.

### Actual Device Behavior

IOS-XE devices allow switchport configuration on shutdown interfaces:

```
interface GigabitEthernet1/0/1
  shutdown                        ← Interface is admin down
  switchport mode access          ← Configuration ACCEPTED
  switchport access vlan 10       ← Configuration ACCEPTED
```

The device stores the configuration even when the interface is shutdown. The configuration becomes active when the interface is brought up with `no shutdown`.

## Conclusion

**`interface_up` is an OPERATIONAL prerequisite, NOT a CONFIGURATION prerequisite.**

### Evidence:
1. Device accepts `switchport mode access` on shutdown interfaces
2. Device accepts `switchport access vlan X` on shutdown interfaces
3. Configuration is stored and becomes active when interface is brought up
4. No configuration rejection occurs due to shutdown state

### Recommendation:

**REMOVE** `interface_up:{interface}` from `configure_access_port` requirements.

**Rationale:**
- The device does not reject the configuration
- The dependency creates false ordering constraints
- Users may intentionally configure shutdown interfaces before bringing them up
- The current dependency forces unnecessary `no shutdown` operations

### Updated Configuration:

```python
"configure_access_port": {
    # ...
    "requires": [
        "vlan_exists:{vlan_id}"  # Only true prerequisite
        # interface_up:{interface} REMOVED
    ],
    "provides": [
        "interface_access_mode:{interface}",
        "interface_vlan_assigned:{interface}:{vlan_id}"
    ]
}
```

## Impact on configure_trunk_port

**Current:**
```python
"configure_trunk_port": {
    "requires": [
        "interface_up:{interface}",  # ← Should also be removed
        "vlans_exist:{allowed_vlans}"
    ]
}
```

**Same logic applies:** Trunk configuration is also accepted on shutdown interfaces.

**Recommendation:** Remove `interface_up:{interface}` from `configure_trunk_port` as well.

## Vendor-Agnostic Approach

This change does NOT introduce vendor-specific exceptions. It corrects the capability model to match actual platform behavior:

- **Before:** Incorrectly assumed admin state blocks configuration
- **After:** Correctly models that admin state is independent of configuration acceptance

The dependency planner will still track `interface_up` as a capability provided by `configure_interface_status`, but it won't be required for switchport configuration.

## Validation

To validate this change:
1. Test `configure_access_port` on a shutdown interface
2. Verify configuration is accepted
3. Verify configuration becomes active after `no shutdown`
4. Confirm no device rejection occurs

This matches the observed behavior described in the issue.
