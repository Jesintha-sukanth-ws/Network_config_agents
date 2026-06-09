# Design Document

## Overview

This design addresses four production defects in the Network Configuration Agent through minimal, behavior-preserving patches. The agent runs a fixed pipeline: Polling → Intent Extraction → Schema/Workflow Validation → CMDB Lookup → Device Facts → State Validation → Retrieval (RAG) → Payload Generation (LLM) → Push → Verify.

The stability patch fixes:
1. Interface summary spacing issues in terminal output
2. Missing per-stage entry/exit logging for debugging hangs
3. Infinite waits due to missing timeouts on external calls
4. Hardcoded SSL verification preventing production deployment

The design preserves the existing architecture, folder structure, pipeline order, and code style while adding minimal changes to improve reliability and observability.

## Architecture

The Network Configuration Agent follows a layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Polling Service                          │
│                 (app/services/polling_service.py)          │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                 Orchestrator Service                        │
│              (app/services/orchestrator_service.py)        │
└─────────────────────────┬───────────────────────────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼────┐    ┌──────────▼──────────┐    ┌─────▼─────┐
│Services│    │    Validation       │    │ Execution │
│        │    │                     │    │           │
│Intent  │    │Schema/Workflow/State│    │Push/Verify│
│CMDB    │    │                     │    │           │
│Display │    │                     │    │           │
└────────┘    └─────────────────────┘    └───────────┘
```

The patch maintains this architecture while adding:
- Stage logging throughout the orchestrator pipeline
- Timeout configuration in settings
- SSL verification configuration
- Improved table formatting in display services

## Components and Interfaces

### 1. Enhanced Settings Module (`config/settings.py`)

**New Configuration Values:**
- `SSL_VERIFY`: Boolean from `SSL_VERIFY` environment variable (default: False)
- Timeout values for external calls (using existing patterns)

**Interface:**
```python
# New exports
SSL_VERIFY: bool
# Existing timeout values remain unchanged
OLLAMA_TIMEOUT: int
SERVICENOW_TIMEOUT: int
DEVICE_TIMEOUT: int
```

### 2. Stage Logger (`app/utils/logger.py`)

**New Component:** `stage_logger` - Python logging.Logger instance for machine-parseable entry/exit logs

**Interface:**
```python
stage_logger = logging.getLogger("stage")

# Usage pattern throughout orchestrator:
stage_logger.info("Entering <stage_name>")
# ... perform stage work ...
stage_logger.info("Completed <stage_name>")
# OR on error:
stage_logger.error("Failed <stage_name>")
```

### 3. Enhanced Orchestration Logger (`app/utils/logger.py`)

**Modified Methods:**
- `format_interface_summary()`: Add minimum spacing between columns
- Preserve existing method signatures and behavior

**Interface (unchanged):**
```python
class OrchestrationLogger:
    @staticmethod
    def format_interface_summary(interfaces: List[Dict]) -> str
    # ... other existing methods unchanged
```

### 4. Enhanced Display Service (`app/services/display_service.py`)

**Modified Functions:**
- `_format_row()`: Ensure minimum one space between columns
- Preserve existing function signatures

**Interface (unchanged):**
```python
def display_terminal_output(result: dict) -> None
def _format_row(values, widths) -> str  # Enhanced implementation
```

### 5. Timeout-Enhanced Services

**Modified Services:**
- `OllamaClient`: Use configured timeout in httpx.Timeout
- `IntentService`: Apply timeout to Ollama calls
- `CMDBService`: Apply timeout to ServiceNow requests (already implemented)
- `RetrievalService`: Add timeout handling for ChromaDB queries

**Interfaces (unchanged):**
All public method signatures remain identical. Timeout handling is internal.

### 6. SSL-Configurable Device Services

**Modified Services:**
- `PushConfigExecutor`: Use `SSL_VERIFY` setting instead of hardcoded `verify=False`
- `ExecutionStatusVerifier`: Use `SSL_VERIFY` setting
- `DeviceStateService`: Use `SSL_VERIFY` setting
- `ConnectionService`: Pass SSL configuration to device calls

**Interfaces (unchanged):**
All public method signatures remain identical. SSL configuration is internal to requests calls.

## Data Models

No new data models are introduced. All existing data structures remain unchanged:

- `CMDBDevice` (Pydantic model) - unchanged
- Orchestrator result structure - unchanged
- Pipeline stage data formats - unchanged
- Connection contract format - unchanged

The patch only modifies internal implementation details while preserving all external interfaces.

## Error Handling

### Timeout Error Handling

**Pattern:** Convert timeout exceptions to structured error results using existing error shapes

```python
# Example for Ollama timeout
try:
    response = self._client.chat(...)
except (httpx.TimeoutException, requests.Timeout) as e:
    return {
        "error": f"LLM request timed out after {timeout}s: {target_url}"
    }
```

**Propagation:** All timeout errors propagate through existing error paths without breaking the orchestrator's error handling contract.

### SSL Verification Error Handling

**Pattern:** Let SSL verification errors propagate naturally through requests

```python
# When SSL_VERIFY=True and certificate is invalid
# requests.exceptions.SSLError will be raised and handled by existing try/catch blocks
```

**Warning Suppression:** When `SSL_VERIFY=False`, suppress urllib3 InsecureRequestWarning once at startup:

```python
if not SSL_VERIFY:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

### Stage Logging Error Handling

**Pattern:** Stage logging failures must not break pipeline execution

```python
try:
    stage_logger.info("Entering stage_name")
except Exception:
    pass  # Never let logging break the pipeline
```

## Testing Strategy

This stability patch focuses on production defect fixes rather than new feature development. The testing approach emphasizes:

### Unit Testing Approach

**Focus Areas:**
- Table formatting functions (`_format_row`, `format_interface_summary`)
- Timeout configuration parsing and application
- SSL verification configuration parsing
- Error handling for timeout and SSL scenarios

**Test Categories:**
- **Formatting Tests**: Verify spacing fixes with various interface name lengths
- **Configuration Tests**: Verify SSL_VERIFY parsing with different environment values
- **Timeout Tests**: Verify timeout values are correctly applied to HTTP clients
- **Error Handling Tests**: Verify structured error responses for timeout scenarios

**Integration Testing:**
- End-to-end pipeline execution with timeouts enabled
- SSL verification behavior in both modes (verify=True/False)
- Stage logging output verification during pipeline execution
- Terminal output format preservation (regression testing)

**No Property-Based Testing:**
This patch addresses specific production defects with deterministic fixes. The changes involve:
- Configuration parsing (deterministic)
- Table formatting (deterministic spacing rules)
- Timeout application (infrastructure configuration)
- SSL verification (boolean configuration)

These are not suitable for property-based testing as they involve infrastructure configuration and deterministic formatting rules rather than algorithmic correctness properties.

**Testing Strategy:**
- **Unit tests** for formatting functions and configuration parsing
- **Integration tests** for end-to-end behavior verification
- **Regression tests** to ensure existing output formats are preserved
- **Mock-based tests** for timeout and SSL error scenarios
