# Requirements Document

## Introduction

The Network Configuration Agent runs a fixed pipeline:
**Polling → Intent Extraction → Schema/Workflow Validation → CMDB Lookup → Device Facts → State Validation → Retrieval (RAG) → Payload Generation (LLM) → Push → Verify.**

Four production-observed defects degrade reliability and observability:

1. The interface summary printed at stage `[5/7] Retrieving Device Facts` concatenates interface name and status when the interface name length meets or exceeds the column width (e.g. `GigabitEthernet0/0unknown`, `GigabitEthernet1/0/5unknown`).
2. The pipeline stops silently after stage `[5/7]` and never reaches `[6/7]` (Retrieval) or `[7/7]` (Payload Generation / Push / Verify). Existing logs do not show whether retrieval, the LLM call, payload generation, or the push is the blocking call.
3. Several external calls have no request-level timeout, in particular Ollama LLM calls and the ServiceNow CMDB lookup, allowing infinite waits.
4. `urllib3` emits `InsecureRequestWarning: Unverified HTTPS request` because `verify=False` is hardcoded at every device-facing `requests` call. There is no way to enable verification per environment.

This spec captures the requirements for a **minimal, behavior-preserving stability patch** that fixes these four issues while keeping the existing folder structure, pipeline order, code style, and dependency surface.

## Glossary

- **Agent**: The Network Configuration Agent process started from `app/main.py`, comprising the polling loop and the orchestrator pipeline.
- **Pipeline**: The fixed ordered sequence of stages executed by `app/services/orchestrator_service.py`: Intent Extraction (1/7), Schema Validation (2/7), Workflow Validation (3/7), CMDB Lookup (4/7), Device Facts (5/7), State Validation (6/7), Payload Generation (7/7), Push (8/9), Verify (9/9).
- **Stage**: One numbered step inside the Pipeline, started via `OrchestrationLogger.step_start`.
- **Display_Service**: `app/services/display_service.py`, responsible for terminal output of the final orchestration result.
- **Orchestration_Logger**: `app/utils/logger.py::OrchestrationLogger`, responsible for printed progress output (banners, step start/success/failure, device facts tables).
- **Stage_Logger**: A `logging.Logger` instance (Python `logging` module) used in addition to `Orchestration_Logger` to emit machine-parseable `INFO`-level entry/exit messages around each Pipeline stage.
- **Interface_Row**: A single line in the interface summary table with columns `Interface | Status | Mode | Access VLAN | Description`.
- **Retrieval_Service**: `app/rag/retrieval_service.py::RetrievalService`, performs ChromaDB queries for RAG context.
- **Payload_Generation_Service**: `app/llm/payload_generation_service.py::PayloadGenerationService`, runs RAG retrieval + Qwen inference + JSON parsing.
- **Qwen_Client**: `app/llm/qwen_client.py::QwenClient`, wrapper around `ollama.Client` used by Payload_Generation_Service.
- **Intent_Service**: `app/services/intent_service.py`, calls Ollama for intent extraction.
- **CMDB_Service**: `app/services/cmdb_service.py`, calls ServiceNow CMDB tables.
- **External_Call**: Any outbound network call made by the Agent, specifically: Ollama chat (`Qwen_Client`, `Intent_Service`), ServiceNow REST (`CMDB_Service`, `polling_service`), and device REST/RESTCONF/NX-API (`connection_service`, `device_state_service`, `push_config`, `execution_status`).
- **Settings**: `config/settings.py`, the single module that loads environment variables via `python-dotenv`.
- **SSL_VERIFY**: A new boolean configuration value loaded by `Settings` from the `SSL_VERIFY` environment variable, controlling the `verify` argument passed to `requests` calls against devices.
- **Sandbox_Mode**: Operating with `SSL_VERIFY=False`, the current default behavior, intended for lab/test devices with self-signed certificates.

## Requirements

### Requirement 1: Interface Summary Spacing

**User Story:** As an operator reading the agent's terminal output, I want each Interface_Row to keep a visible separator between the interface name and the status column, so that I can read the interface and its operational status correctly even when the interface name is long.

#### Acceptance Criteria

1. WHEN the Orchestration_Logger prints an Interface_Row, THE Orchestration_Logger SHALL emit at least one space character between the interface name and the status value.
2. WHEN the Orchestration_Logger prints an Interface_Row whose interface name length is greater than or equal to the name column width, THE Orchestration_Logger SHALL still emit at least one space character between the interface name and the status value.
3. THE Orchestration_Logger SHALL apply the same single-space-minimum rule between every adjacent pair of columns in the interface summary table (Interface, Status, Mode, Access VLAN, Description).
4. THE Display_Service SHALL apply the same single-space-minimum rule between every adjacent pair of columns in the "RELEVANT INTERFACES" table it prints.
5. THE Orchestration_Logger SHALL preserve the existing column order, column labels, and overall table structure of the interface summary.
6. THE Orchestration_Logger SHALL NOT hardcode any specific interface name, vendor, model, or platform string while implementing the spacing fix.
7. WHERE an interface field is missing or null, THE Orchestration_Logger SHALL render it as the existing placeholder (`-` for `format_interface_summary`, `unknown` / `N/A` for `Display_Service`) without altering the placeholder text.

### Requirement 2: Per-Stage Entry and Exit Logging

**User Story:** As an operator debugging a hang, I want every Pipeline stage to emit an `INFO`-level entry log before it begins and an `INFO`-level exit log when it completes (or fails), so that I can identify the exact stage where the Agent stops responding.

#### Acceptance Criteria

1. WHEN the orchestrator begins any Pipeline stage, THE Stage_Logger SHALL emit one `INFO` log line containing the literal text `Entering` and the stage name before any external call for that stage is issued.
2. WHEN any Pipeline stage finishes successfully, THE Stage_Logger SHALL emit one `INFO` log line containing the literal text `Completed` and the stage name after the stage's last external call returns.
3. IF any Pipeline stage raises an exception or returns an error result, THEN THE Stage_Logger SHALL emit one `ERROR` log line containing the literal text `Failed` and the stage name before the orchestrator returns or moves on.
4. THE Stage_Logger SHALL emit entry and exit logs for at minimum the following stages: Intent Extraction, Schema Validation, Workflow Validation, CMDB Lookup, Device Facts, State Validation, RAG Retrieval, LLM Inference, Payload Generation, Push Configuration, Verify Execution.
5. WHEN Payload_Generation_Service performs RAG retrieval, THE Stage_Logger SHALL emit `Entering retrieval stage` before the ChromaDB query and `Retrieval completed` after the query returns.
6. WHEN Payload_Generation_Service invokes Qwen_Client, THE Stage_Logger SHALL emit `Starting LLM inference` before the Ollama chat call and `LLM inference completed` after the response is received.
7. WHEN Payload_Generation_Service finishes parsing and validating the LLM JSON output for a step, THE Stage_Logger SHALL emit `Payload generation completed` for that step.
8. WHEN the orchestrator pushes a payload via `PushConfigExecutor`, THE Stage_Logger SHALL emit an entry log before the push and an exit log after the push.
9. WHEN the orchestrator verifies a push via `ExecutionStatusVerifier`, THE Stage_Logger SHALL emit an entry log before the verification call and an exit log after it returns.
10. THE Stage_Logger SHALL emit entry and exit logs even when a stage is skipped due to upstream errors, replacing the exit log with one `INFO` log line containing the literal text `Skipped` and the reason.
11. THE Stage_Logger SHALL use the standard Python `logging` module so that timestamps, log level, and module name are included in every emitted line.
12. THE Stage_Logger SHALL NOT replace, suppress, or remove any existing `OrchestrationLogger` print output; the new logs SHALL be additive.

### Requirement 3: Timeouts on All External Calls

**User Story:** As an operator, I want every External_Call made by the Agent to time out within a bounded duration, so that no single hung remote service can stall the Pipeline indefinitely.

#### Acceptance Criteria

1. THE Agent SHALL apply a finite, positive timeout to every External_Call.
2. WHEN Qwen_Client invokes the Ollama chat API, THE Qwen_Client SHALL pass a timeout value derived from `OLLAMA_TIMEOUT` to the underlying HTTP transport, so that the call cannot wait indefinitely.
3. WHEN Intent_Service invokes the Ollama chat API, THE Intent_Service SHALL apply a timeout value derived from `OLLAMA_TIMEOUT` to the underlying HTTP transport.
4. WHEN CMDB_Service issues an HTTP request to ServiceNow, THE CMDB_Service SHALL pass a `timeout` argument to every `requests.*` call.
5. WHEN Retrieval_Service performs a ChromaDB query, THE Retrieval_Service SHALL either use a Chroma client configured with a finite timeout or wrap the query so the orchestrator can detect a stuck retrieval.
6. THE Agent SHALL read External_Call timeout values from Settings rather than hardcoding magic numbers inside service modules.
7. IF Settings does not define an explicit timeout for an External_Call, THEN THE service module SHALL use the existing default value already present in the codebase (no shorter, no longer) so behavior is preserved.
8. THE Agent SHALL convert any External_Call failure (including timeouts, connection errors, and HTTP errors) into a structured error result and propagate it through the existing error path, so that no uncaught exception escapes into the polling loop.
9. IF an External_Call exceeds its configured timeout, THEN the calling service SHALL produce a structured error result containing the timeout value and the call target, using the same error shape already returned by that service today.
10. THE timeout values defined by Settings SHALL be at least 1 second and at most 600 seconds.
11. THE patch SHALL NOT shorten any timeout value already present in the codebase.

### Requirement 4: Configurable TLS Verification for Device Calls

**User Story:** As an operator, I want TLS certificate verification on device-facing HTTPS calls to be controlled by a single environment variable, so that I can keep `verify=False` for sandbox/test devices and enable verification in production without editing source code.

#### Acceptance Criteria

1. THE Settings SHALL expose a boolean named `SSL_VERIFY` loaded from the `SSL_VERIFY` environment variable.
2. WHERE the `SSL_VERIFY` environment variable is unset, THE Settings SHALL default `SSL_VERIFY` to `False` so that current sandbox behavior is preserved.
3. WHEN a device-facing HTTPS call is issued by `connection_service.py`, `device_state_service.py`, `push_config.py`, or any other module under `app/devices/` or `app/execution/`, THE calling module SHALL pass `verify=SSL_VERIFY` to every `requests.*` call instead of the literal `False`.
4. WHERE a module under `app/devices/` or `app/execution/` issues an HTTP request to ServiceNow rather than to a network device, THE calling module SHALL continue to use the `requests` default for `verify` (which is `True`) and SHALL NOT pass `SSL_VERIFY`.
5. IF `SSL_VERIFY` is `False`, THEN THE Agent SHALL suppress the `urllib3.exceptions.InsecureRequestWarning` once at startup so that the warning does not flood the terminal output during operation.
6. IF `SSL_VERIFY` is `True`, THEN THE Agent SHALL NOT suppress `InsecureRequestWarning` and SHALL allow `requests` to perform certificate verification normally.
7. THE patch SHALL recognize at least the values `true`, `false`, `1`, `0`, `yes`, `no` (case-insensitive) when parsing the `SSL_VERIFY` environment variable.
8. THE patch SHALL NOT change `verify=False` to `verify=True` for ServiceNow calls in `cmdb_service.py` or `polling_service.py`; ServiceNow calls SHALL continue to use the `requests` default for `verify` (which is `True`) as they do today.
9. THE `.env` file SHALL be updated to document `SSL_VERIFY` with its default value, but the patch SHALL NOT commit any real device or ServiceNow credentials into the repository.

### Requirement 5: Architecture Preservation Constraints

**User Story:** As the project owner, I want the stability patch to leave the existing architecture untouched, so that the team's mental model, deployment process, and review effort remain unchanged.

#### Acceptance Criteria

1. THE patch SHALL preserve the exact existing top-level folder structure: `app/devices/`, `app/execution/`, `app/llm/`, `app/network_validation/`, `app/prompts/`, `app/rag/`, `app/registry/`, `app/services/`, `app/utils/`, `app/validation/`, `config/`.
2. THE patch SHALL NOT add any new top-level folder under `app/` or `config/`.
3. THE patch SHALL NOT delete, rename, or relocate any existing source file under `app/` or `config/`.
4. THE patch SHALL preserve the existing Pipeline order exactly as defined in `app/services/orchestrator_service.py`: Intent Extraction → Schema Validation → Workflow Validation → CMDB Lookup → Device Facts → State Validation → Payload Generation → Push → Verify.
5. THE patch SHALL NOT introduce any dependency-injection framework, container, service locator, or runtime registry not already present in the codebase.
6. THE patch SHALL NOT introduce any orchestration framework (Celery, Prefect, Dagster, Airflow, asyncio task graphs, etc.) not already present in the codebase.
7. THE patch SHALL NOT add a new third-party Python package outside those already imported by the existing modules; it MAY use modules from the standard library and from packages already in use (`requests`, `ollama`, `python-dotenv`, `urllib3`, `pydantic`, `chromadb`, `sentence-transformers`).
8. THE patch SHALL preserve the existing beginner-readable code style: no metaclasses, no decorators added beyond `@staticmethod`, no abstract base classes added, no generic typing beyond what is already used.
9. THE patch SHALL keep the diff minimal: each touched file SHALL change only the lines required by Requirements 1, 2, 3, or 4, plus directly supporting imports and helper functions.
10. THE patch SHALL NOT alter the public function or method signatures of: `orchestrator_service.process_task`, `intent_service.parse_intent`, `cmdb_service.get_cmdb_data`, `device_state_service.get_device_facts`, `connection_service.build_connection`, `connection_service.connect_to_device`, `PayloadGenerationService.generate`, `QwenClient.generate`, `RetrievalService.retrieve`, `RetrievalService.retrieve_raw_context`, `PushConfigExecutor.execute`, `ExecutionStatusVerifier.verify`, `OrchestrationLogger.format_interface_summary`, `display_service.display_terminal_output`.

### Requirement 6: Backward Compatibility of Outputs

**User Story:** As an operator who has scripts and screenshots that depend on the agent's existing terminal output, I want the patch to keep all unchanged stages producing the same output, so that downstream tooling and runbooks do not need updates.

#### Acceptance Criteria

1. WHEN the Pipeline runs successfully end-to-end with valid inputs, THE Display_Service SHALL produce the same final orchestration result block as it does today, except for the spacing fix mandated by Requirement 1.
2. THE patch SHALL preserve the existing stage banners (`[1/7] Extracting Intent...`, `[2/7] Validating Schema...`, etc.) printed by `OrchestrationLogger.step_start`.
3. THE patch SHALL preserve the existing column headers, separators, and emoji prefixes used in `display_service.py` and `OrchestrationLogger`.
4. THE patch SHALL preserve the existing JSON structure returned by `orchestrator_service.process_task` (top-level keys: `task`, `intent`, `device`, `device_facts`, `execution_plan`, `generated_payloads`, `execution_results`, `execution`).
5. WHEN the Agent runs in Sandbox_Mode (the default), THE Agent SHALL produce no `InsecureRequestWarning` lines on stderr.
