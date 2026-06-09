# Canonical Name Audit: configure_interface_status

## Problem Summary

The `rag_type` value (`interface_mode`) was leaking into execution layers, causing operation name mismatches.

### Observed Failures

1. **Payload Generator**: Returned `operation: "interface_mode"` instead of `operation: "configure_interface_status"`
2. **PushConfig**: Expected `configure_interface_status` but received `interface_mode`
3. **ExecutionStatusVerifier**: Dispatch table referenced wrong method name and used `rag_type` values

## Root Causes

### 1. Orchestrator (orchestrator_service.py:354)
```python
# BEFORE (WRONG)
payload = _get_payload_service().generate({
    "intent_type": rag_type,  # ← Passing rag_type instead of canonical name
    "parameters": step.get("parameters", {}),
    "device": payload_device
})

# AFTER (CORRECT)
payload = _get_payload_service().generate({
    "intent_type": intent_type,  # ← Use canonical name for operation field
    "rag_type": rag_type,         # ← Use rag_type for document retrieval only
    "parameters": step.get("parameters", {}),
    "device": payload_device
})
```

### 2. Payload Generation Service (payload_generation_service.py:36)
```python
# BEFORE (WRONG)
context = self._retriever.retrieve_raw_context(
    intent_type=intent_type,  # ← Using intent_type for RAG lookup
    vendor=device["vendor"],
    os_name=device["os"],
    version=device["version"]
)

# AFTER (CORRECT)
intent_type = orchestration_input["intent_type"]  # Canonical name
rag_type = orchestration_input.get("rag_type", intent_type)  # RAG lookup key

context = self._retriever.retrieve_raw_context(
    intent_type=rag_type,  # ← Use rag_type for document retrieval
    vendor=device["vendor"],
    os_name=device["os"],
    version=device["version"]
)
```

### 3. Execution Status Verifier (execution_status.py:48)
```python
# BEFORE (WRONG)
self._handlers = {
    "create_vlan": self._verify_vlan_creation,
    "delete_vlan": self._verify_vlan_deletion,
    "access_port": self._verify_access_port,           # ← rag_type value
    "trunk_port": self._verify_trunk_port,             # ← rag_type value
    "configure_interface_status": self._interface_mode # ← Wrong method name
}

# AFTER (CORRECT)
self._handlers = {
    "create_vlan": self._verify_vlan_creation,
    "delete_vlan": self._verify_vlan_deletion,
    "configure_access_port": self._verify_access_port,        # ← Canonical name
    "configure_trunk_port": self._verify_trunk_port,          # ← Canonical name
    "configure_interface_status": self._verify_interface_mode # ← Correct method name
}
```

### 4. PushConfig Executor (push_config.py:213)
```python
# BEFORE (WRONG)
dispatch = {
    "create_vlan":    self._restconf_create_vlan,
    "delete_vlan":    self._restconf_delete_vlan,
    "access_port":    self._restconf_access_port,    # ← rag_type value
    "trunk_port":     self._restconf_trunk_port,     # ← rag_type value
    "interface_mode": self._restconf_interface_mode, # ← rag_type value
}

# AFTER (CORRECT)
dispatch = {
    "create_vlan":                  self._restconf_create_vlan,
    "delete_vlan":                  self._restconf_delete_vlan,
    "configure_access_port":        self._restconf_access_port,       # ← Canonical name
    "configure_trunk_port":         self._restconf_trunk_port,        # ← Canonical name
    "configure_interface_status":   self._restconf_interface_mode,    # ← Canonical name
}
```

## Architecture Principles

### Single Source of Truth
- **Registry**: Defines both `canonical name` and `rag_type`
- **Canonical Name**: Used everywhere except RAG retrieval
- **RAG Type**: Used ONLY for document retrieval

### Data Flow

```
User Input
    ↓
Intent Service → canonical: "configure_interface_status"
    ↓
Registry Lookup → rag_type: "interface_mode"
    ↓
┌─────────────────────────────────────────┐
│ Orchestrator                            │
│   intent_type: "configure_interface_status" │
│   rag_type: "interface_mode"            │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Payload Generation Service              │
│   - RAG Retrieval: use rag_type         │
│   - Prompt: use intent_type             │
│   - Output: operation = intent_type     │
└─────────────────────────────────────────┘
         ↓
Generated Payload:
{
  "operation": "configure_interface_status",  ← Canonical name
  "payload": { "interface": "...", "administrative_state": "..." }
}
         ↓
┌─────────────────────────────────────────┐
│ PushConfig Executor                     │
│   Dispatch on: "configure_interface_status" │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Execution Status Verifier               │
│   Dispatch on: "configure_interface_status" │
└─────────────────────────────────────────┘
```

## Verification

### All Operation Names Now Use Canonical Names

| Component | Operation Name |
|-----------|----------------|
| Registry | `configure_interface_status` |
| Orchestrator | `configure_interface_status` |
| Payload Generator (output) | `configure_interface_status` |
| PushConfig Executor | `configure_interface_status` |
| Execution Verifier | `configure_interface_status` |

### RAG Type Used ONLY for Retrieval

| Component | Uses rag_type? | Purpose |
|-----------|----------------|---------|
| Orchestrator | ✅ Yes | Pass to payload generator |
| Payload Generator | ✅ Yes | Document retrieval only |
| Prompt Template | ❌ No | Uses intent_type |
| PushConfig | ❌ No | Uses intent_type |
| Verifier | ❌ No | Uses intent_type |

## Files Modified

1. **app/services/orchestrator_service.py**
   - Pass both `intent_type` and `rag_type` to payload generator
   - Use `intent_type` for operation field

2. **app/llm/payload_generation_service.py**
   - Accept both `intent_type` and `rag_type`
   - Use `rag_type` for RAG retrieval
   - Use `intent_type` for prompt and operation field

3. **app/execution/push_config.py**
   - Updated RESTCONF dispatch table to use canonical names
   - Updated NXAPI dispatch table to use canonical names

4. **app/execution/execution_status.py**
   - Updated dispatch table to use canonical names
   - Fixed method reference: `_interface_mode` → `_verify_interface_mode`

5. **app/registry/intent_registry.py**
   - Added SOP payload contracts to all operations

## Test Coverage

To verify the fixes work:

1. Submit task with `configure_interface_status` intent
2. Verify payload has `"operation": "configure_interface_status"`
3. Verify PushConfig accepts the operation
4. Verify ExecutionStatusVerifier accepts the operation
5. Verify end-to-end execution succeeds

## Benefits

✅ **Single source of truth** - Operation names defined once in registry
✅ **Clear separation** - RAG type used only for retrieval
✅ **No leakage** - RAG type never appears in payloads or execution
✅ **Consistent naming** - All components use canonical names
✅ **No aliases** - One operation name throughout the pipeline
