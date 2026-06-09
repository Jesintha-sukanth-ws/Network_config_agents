# Bugfix Requirements Document

## Introduction

RAG retrieval returns 0 chunks due to version mismatch between device-reported versions and Chroma metadata versions. The device reports version `17.15.01` which is normalized to `17.15` by DeviceStateService, but Chroma metadata stores the full version `17.15.01` from PDF documents. This mismatch causes exact-match filters to fail, resulting in empty RAG context, LLM hallucinations, and executor failures.

**Impact:**
- Payload generation receives empty context (`context_chars = 0`)
- LLM hallucinates payload structures without SOP guidance
- Executor rejects payloads with errors like "Missing interface in payload"
- All intents affected: `interface_mode`, `access_port`, `create_vlan`, `delete_vlan`, `trunk_port`

**Diagnostic Evidence:**
- Test 1 (device version 17.15): **0 results** (MISMATCH)
- Test 2 (PDF version 17.15.01): **5 results** (MATCH)
- Test 3 (intent + device version): **0 results** (MISMATCH)
- Test 4 (intent + PDF version): **5 results** (MATCH)
- Test 5 (no version filter): **5 results** (WORKS)

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a device reports version `17.15.01` THEN DeviceStateService normalizes it to `17.15` in `_normalize_device_info`

1.2 WHEN DocumentParser ingests a PDF with `VERSION: 17.15.01` metadata THEN it stores the full version `17.15.01` in Chroma without normalization

1.3 WHEN RetrievalService queries Chroma with device version `17.15` THEN the exact-match filter `{"VERSION": "17.15"}` fails to match metadata `{"VERSION": "17.15.01"}`

1.4 WHEN the version filter fails to match THEN RetrievalService returns 0 chunks for all intents

1.5 WHEN payload generation receives 0 chunks THEN the LLM generates payloads without SOP context, leading to hallucinated structures

1.6 WHEN the executor receives hallucinated payloads THEN it rejects them with validation errors

### Expected Behavior (Correct)

2.1 WHEN any component processes a version string THEN it SHALL use a shared `normalize_version()` utility function

2.2 WHEN `normalize_version()` receives version `17.15.01` THEN it SHALL return `17.15` (major.minor only)

2.3 WHEN `normalize_version()` receives version `17.15` THEN it SHALL return `17.15` (already normalized)

2.4 WHEN `normalize_version()` receives version `9.3.12` THEN it SHALL return `9.3` (major.minor only)

2.5 WHEN DeviceStateService normalizes device version THEN it SHALL use `normalize_version()` instead of local parsing logic

2.6 WHEN DocumentParser extracts VERSION metadata from PDFs THEN it SHALL normalize the version using `normalize_version()` before storing in Chroma

2.7 WHEN RetrievalService receives a version parameter THEN it SHALL normalize the version using `normalize_version()` before constructing filters

2.8 WHEN all components use the same normalization logic THEN version queries SHALL match Chroma metadata consistently

2.9 WHEN version queries match consistently THEN RetrievalService SHALL return relevant chunks for all intents

2.10 WHEN relevant chunks are returned THEN payload generation SHALL receive valid SOP context and generate correct payloads

### Unchanged Behavior (Regression Prevention)

3.1 WHEN RetrievalService queries with intent filters THEN it SHALL CONTINUE TO filter by intent metadata fields (`intent`, `INTENT`, `feature`, `FEATURE`, `topic`, `TOPIC`)

3.2 WHEN RetrievalService queries with vendor and OS parameters THEN it SHALL CONTINUE TO resolve the correct Chroma collection name

3.3 WHEN DocumentParser extracts metadata from PDFs THEN it SHALL CONTINUE TO extract all supported metadata fields (`VENDOR`, `VERSION`, `OS`, `TOPIC`, `FEATURE`, `INTENT`)

3.4 WHEN DocumentParser processes text blocks THEN it SHALL CONTINUE TO deduplicate content using SHA-256 hashing

3.5 WHEN DeviceStateService normalizes device info THEN it SHALL CONTINUE TO extract hostname, model, and serial number

3.6 WHEN DeviceStateService normalizes VLANs THEN it SHALL CONTINUE TO extract VLAN ID and name

3.7 WHEN DeviceStateService normalizes interfaces THEN it SHALL CONTINUE TO extract interface name, description, mode, status, access_vlan, allowed_vlans, and native_vlan

3.8 WHEN version normalization is applied THEN it SHALL NOT introduce hardcoded version mappings or special-case logic

3.9 WHEN version normalization is applied THEN it SHALL NOT weaken retrieval filters or affect vendor-agnostic behavior

3.10 WHEN the fix is implemented THEN existing PDFs SHALL require re-ingestion to normalize stored metadata
