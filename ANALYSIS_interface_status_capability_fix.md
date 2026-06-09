# Analysis: configure_interface_status Capability Model Fix

## Problem Identified

The `configure_interface_status` intent had a **logical inconsistency** in its capability model.

### Before Fix

```python
"configure_interface_status": {
    "requires": [],
    "provides": [
        "interface_up:{interface}",
        "interface_status:{interface}:{administrative_state}"
    ]
}
```

### The Contradiction

When a user shuts down an interface:

```python
Input: {
    "interface": "GigabitEthernet1/0/1",
    "administrative_state": "down"
}

Provides: [
    "interface_up:GigabitEthernet1/0/1",      # ❌ Claims interface is UP
    "interface_status:GigabitEthernet1/0/1:down"  # ❌ Claims interface is DOWN
]
```

**These capabilities contradict each other!**

## Root Cause Analysis

### Investigation: Can Dependency Planner Support Conditional Capabilities?

Reviewed `app/workflow/dependency_planner.py` to determine if conditional capabilities based on parameter values are supported.

**Finding**: The `_resolve_capabilities()` method (lines 280-320) performs **simple string substitution** only. It does NOT evaluate parameter values to conditionally generate different capabilities.

```python
def _resolve_capabilities(self, capability_patterns, parameters):
    """
    Resolve capability patterns by substituting parameter values.
    
    Examples:
        "vlan_exists:{vlan_id}" with params {"vlan_id": 87}
        → "vlan_exists:87"
    """
    # Simple parameter substitution - NO conditional logic
```

**Conclusion**: Conditional capabilities (e.g., "if administrative_state == 'up' then provide interface_up") are **NOT supported** by the current architecture.

## Solution Implemented

Since conditional capabilities are not supported, the correct solution is to **remove the ambiguous capability** and keep only the explicit one.

### After Fix

```python
"configure_interface_status": {
    "requires": [],
    "provides": [
        "interface_status:{interface}:{administrative_state}"
    ]
}
```

### Benefits

1. **Eliminates Contradiction**: No more conflicting capabilities
   - `administrative_state="down"` → provides `interface_status:...:down` (consistent)
   - `administrative_state="up"` → provides `interface_status:...:up` (consistent)

2. **Preserves Information**: All state information is encoded in `interface_status`
   - `interface_status:Gi1/0/1:up` = interface is up
   - `interface_status:Gi1/0/1:down` = interface is down

3. **Backward Compatibility**: Existing workflows continue to work
   - Dependency planner has fallback logic in `_find_provider()` (lines 502-516)
   - Automatically matches `interface_up:{interface}` requirements with `interface_status:{interface}:up` providers

4. **No Changes to Dependency Planner**: Solution works within existing architecture

## Architecture

### Three-Layer Capability Model

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Device State (Operational)                        │
│ - Extracts interface_up from actual device state           │
│ - Used for: Detecting current operational state            │
│ - Source: DeviceStateService                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Workflow Steps (Configuration Intent)             │
│ - Provides interface_status:{interface}:{state}             │
│ - Used for: Declaring configuration intent                 │
│ - Source: Intent Registry                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Dependency Planner (Matching Logic)               │
│ - Matches interface_up requirements with:                  │
│   1. Device state interface_up (exact match)               │
│   2. Workflow interface_status:...:up (fallback match)     │
│ - Source: DependencyPlanner._find_provider()               │
└─────────────────────────────────────────────────────────────┘
```

### Example Workflow

**Scenario**: User wants to configure an access port on a shutdown interface

```python
Workflow:
1. configure_interface_status(interface="Gi1/0/1", administrative_state="up")
2. configure_access_port(interface="Gi1/0/1", vlan_id=87)

Step 1 provides: interface_status:Gi1/0/1:up
Step 2 requires: vlan_exists:87 (no interface_up requirement after Task 2 fix)

Result: ✅ Workflow is valid
```

**Scenario**: Legacy workflow that requires interface_up

```python
Workflow:
1. configure_interface_status(interface="Gi1/0/1", administrative_state="up")
2. Some legacy step that requires interface_up:Gi1/0/1

Step 1 provides: interface_status:Gi1/0/1:up
Step 2 requires: interface_up:Gi1/0/1

Planner logic:
- Checks capability_providers for "interface_up:Gi1/0/1" → not found
- Fallback: Checks for "interface_status:Gi1/0/1:*" → finds "interface_status:Gi1/0/1:up"
- Extracts state "up" → matches requirement

Result: ✅ Backward compatibility maintained
```

## Validation Results

All tests pass:

```
[TEST 1] Verify interface_up removed from configure_interface_status
✓ PASSED - Only interface_status in provides (no contradiction)

[TEST 2] Verify capability resolution for administrative_state='up'
✓ PASSED - Provides interface_status:...:up (no interface_up)

[TEST 3] Verify capability resolution for administrative_state='down'
✓ PASSED - Provides interface_status:...:down (no interface_up)

[TEST 4] Verify planner matches interface_up with interface_status:...:up
✓ PASSED - Planner matched 'interface_up:...' with interface_status:...:up

[TEST 5] Verify device state extraction still provides interface_up
✓ PASSED - Device state still provides interface_up
```

## Files Modified

1. **app/registry/intent_registry.py**
   - Removed `interface_up:{interface}` from `configure_interface_status` provides
   - Updated documentation to reflect new architecture
   - Added explanatory comments

## Files NOT Modified

1. **app/workflow/dependency_planner.py**
   - No changes needed
   - Existing `_find_provider()` fallback logic handles backward compatibility
   - `_extract_state_capabilities()` still extracts `interface_up` from device state

## Related Changes

This fix complements **Task 2: interface_up Dependency Removal**:

- **Task 2**: Removed `interface_up:{interface}` from `configure_access_port` and `configure_trunk_port` **requirements**
  - Rationale: Devices accept switchport config on shutdown interfaces
  - `interface_up` is operational, not a configuration prerequisite

- **Task 3** (this fix): Removed `interface_up:{interface}` from `configure_interface_status` **provides**
  - Rationale: Eliminates logical contradiction
  - `interface_status` encodes the actual state without ambiguity

Together, these changes create a **consistent, contradiction-free capability model**.

## Design Principles Followed

1. ✅ **No Vendor-Specific Exceptions**: Solution reflects actual platform behavior
2. ✅ **DRY Compliance**: Single source of truth for capability definitions
3. ✅ **Backward Compatibility**: Existing workflows continue to work
4. ✅ **Minimal Changes**: Works within existing architecture
5. ✅ **Explicit Over Implicit**: State is explicitly encoded in capability names

## Conclusion

The fix eliminates a logical inconsistency in the capability model while maintaining backward compatibility and requiring no changes to the dependency planner. The three-layer architecture (device state, workflow intent, planner matching) provides clear separation of concerns and robust dependency resolution.
