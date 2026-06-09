# RAG Version Normalization Bugfix Design

## Overview

This bugfix addresses version mismatch failures in RAG retrieval by eliminating duplicated version normalization logic across the codebase. Currently, three components implement their own version parsing (DeviceStateService, IngestionService, and DocumentParser), while RetrievalService lacks normalization entirely. This inconsistency causes exact-match filter failures when device-reported versions (e.g., `17.15`) don't match Chroma metadata versions (e.g., `17.15.01`), resulting in zero RAG chunks, LLM hallucinations, and executor failures.

The fix introduces a single shared utility function `normalize_version()` in `app/utils/version_utils.py` that all components will use. This ensures consistent major.minor normalization across device state collection, PDF ingestion, document parsing, and retrieval queries. After implementation, existing PDFs must be re-ingested to normalize stored Chroma metadata.

## Glossary

- **Bug_Condition (C)**: Version string processing occurs in any component (DeviceStateService, IngestionService, DocumentParser, RetrievalService) where normalization logic is either duplicated or missing
- **Property (P)**: All version strings are normalized to major.minor format (e.g., `17.15.01` → `17.15`) using the shared `normalize_version()` utility function
- **Preservation**: Existing metadata extraction, collection resolution, intent filtering, and device state normalization behaviors remain unchanged
- **normalize_version()**: Shared utility function in `app/utils/version_utils.py` that extracts major.minor components from version strings
- **DeviceStateService**: Service in `app/devices/device_state_service.py` that normalizes device information including OS version
- **IngestionService**: Service in `app/rag/ingestion_service.py` that extracts metadata from PDF filenames during ingestion
- **DocumentParser**: Parser in `app/rag/document_parser.py` that extracts VERSION metadata from PDF content blocks
- **RetrievalService**: Service in `app/rag/retrieval_service.py` that queries Chroma collections with version filters
- **Chroma metadata**: Key-value metadata stored with each document chunk in ChromaDB (includes VERSION, VENDOR, OS, INTENT fields)

## Bug Details

### Bug Condition

The bug manifests when version strings are processed inconsistently across the RAG pipeline. DeviceStateService normalizes device versions to major.minor format using inline parsing logic (`parts = raw_version.split("."); ".".join(parts[:2])`), while IngestionService duplicates this logic for PDF filename metadata. DocumentParser extracts VERSION metadata from PDF content but stores the full version without normalization. RetrievalService receives normalized device versions but queries against non-normalized Chroma metadata, causing exact-match filter failures.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type VersionProcessingContext
  OUTPUT: boolean
  
  RETURN (input.component IN ['DeviceStateService', 'IngestionService', 'DocumentParser', 'RetrievalService'])
         AND (input.hasInlineNormalization OR input.lacksNormalization)
         AND NOT input.usesSharedUtility
END FUNCTION
```

### Examples

- **DeviceStateService (Lines 287-289)**: Device reports `17.15.01` → inline parsing normalizes to `17.15` → stored in device state
- **IngestionService (Lines 215-218)**: PDF filename contains `VERSION: 17.15.01` → inline parsing normalizes to `17.15` → stored in Chroma metadata
- **DocumentParser**: PDF content block contains `VERSION: 17.15.01` → no normalization → stored as `17.15.01` in Chroma metadata (MISMATCH)
- **RetrievalService**: Receives device version `17.15` → queries Chroma with filter `{"VERSION": "17.15"}` → fails to match `{"VERSION": "17.15.01"}` → returns 0 chunks (FAILURE)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- RetrievalService must continue to filter by intent metadata fields (`intent`, `INTENT`, `feature`, `FEATURE`, `topic`, `TOPIC`)
- RetrievalService must continue to resolve collection names from vendor and OS parameters using `_resolve_collection_name()`
- DocumentParser must continue to extract all supported metadata fields (`VENDOR`, `VERSION`, `OS`, `TOPIC`, `FEATURE`, `INTENT`)
- DocumentParser must continue to deduplicate content using SHA-256 hashing
- DeviceStateService must continue to extract hostname, model, serial number, VLANs, and interfaces
- IngestionService must continue to extract metadata from PDF filenames and build chunks
- Version normalization must not introduce hardcoded version mappings or vendor-specific logic

**Scope:**
All inputs that do NOT involve version string processing should be completely unaffected by this fix. This includes:
- Metadata extraction for non-version fields (VENDOR, OS, INTENT, etc.)
- Collection name resolution based on vendor and OS
- Intent filtering and semantic search
- Device state extraction for non-version fields (hostname, interfaces, VLANs)
- Content deduplication and chunk building

## Hypothesized Root Cause

Based on the bug description and code audit, the root causes are:

1. **Code Duplication**: The version normalization logic (`parts = version.split("."); ".".join(parts[:2])`) is duplicated in DeviceStateService (lines 287-289) and IngestionService (lines 215-218), violating DRY principles and creating maintenance burden.

2. **Missing Normalization in DocumentParser**: The `_extract_metadata_from_block()` method extracts VERSION metadata from PDF content blocks but stores the raw value without normalization, causing mismatches with device-reported versions.

3. **Missing Normalization in RetrievalService**: The `retrieve()` method receives version parameters from upstream components but does not normalize them before constructing Chroma filters, assuming upstream normalization is consistent (which it isn't).

4. **Lack of Shared Utility**: No centralized `normalize_version()` function exists in `app/utils/`, forcing each component to implement its own parsing logic or skip normalization entirely.

## Correctness Properties

Property 1: Bug Condition - Shared Version Normalization

_For any_ version string processed by DeviceStateService, IngestionService, DocumentParser, or RetrievalService, the component SHALL use the shared `normalize_version()` utility function to normalize the version to major.minor format (e.g., `17.15.01` → `17.15`), ensuring consistent normalization across the entire RAG pipeline.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8**

Property 2: Preservation - Non-Version Metadata and Filtering

_For any_ metadata extraction, collection resolution, or filtering operation that does NOT involve version strings, the fixed code SHALL produce exactly the same behavior as the original code, preserving intent filtering, vendor/OS resolution, content deduplication, and device state extraction for all non-version fields.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File 1**: `app/utils/version_utils.py` (NEW FILE)

**Function**: `normalize_version(version: str) -> str`

**Specific Changes**:
1. **Create Shared Utility Module**: Create new file `app/utils/version_utils.py` with `normalize_version()` function
   - Accept version string as input (e.g., `"17.15.01"`, `"17.15"`, `"9.3.12"`)
   - Handle None and empty string inputs gracefully (return as-is)
   - Split version string on `.` delimiter
   - Extract first two components (major.minor)
   - Return normalized version or original if less than 2 components
   - Include docstring with examples and type hints

**File 2**: `app/devices/device_state_service.py`

**Function**: `_normalize_device_info()`

**Specific Changes**:
1. **Import Shared Utility**: Add `from app.utils.version_utils import normalize_version` at top of file
2. **Remove Inline Parsing**: Delete lines 287-289 (inline version parsing logic)
3. **Use Shared Function**: Replace with `info["os_version"] = normalize_version(raw_version)`
   - Simplifies code from 3 lines to 1 line
   - Eliminates duplicated parsing logic
   - Ensures consistency with other components

**File 3**: `app/rag/ingestion_service.py`

**Function**: `_extract_metadata_from_filename()`

**Specific Changes**:
1. **Import Shared Utility**: Add `from app.utils.version_utils import normalize_version` at top of file
2. **Remove Inline Parsing**: Delete lines 216-217 (inline version parsing logic)
3. **Use Shared Function**: Replace with `norm_ver = normalize_version(raw_ver)`
   - Simplifies code from 2 lines to 1 line
   - Eliminates duplicated parsing logic
   - Ensures consistency with other components

**File 4**: `app/rag/document_parser.py`

**Function**: `_extract_metadata_from_block()`

**Specific Changes**:
1. **Import Shared Utility**: Add `from app.utils.version_utils import normalize_version` at top of file
2. **Add Normalization Logic**: After extracting VERSION metadata (line ~210), normalize the value before storing
   - Check if `key == "VERSION"` after metadata pattern match
   - Apply `value = normalize_version(value)` before storing in `global_metadata`
   - Ensures PDF content metadata is normalized consistently with filename metadata

**Note on RetrievalService**: Data flow analysis confirms RetrievalService receives already-normalized version values from DeviceStateService (via OrchestratorService → PayloadGenerationService). No changes required to RetrievalService. The fix focuses on normalizing at the source (DeviceStateService for device versions, DocumentParser/IngestionService for PDF metadata).

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code by verifying version mismatches cause retrieval failures, then verify the fix works correctly by confirming all components use shared normalization and retrieval succeeds with consistent versions.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that duplicated/missing normalization logic causes version mismatches and retrieval failures.

**Test Plan**: Write tests that simulate the full RAG pipeline (device state collection → PDF ingestion → retrieval) with version strings that require normalization. Run these tests on the UNFIXED code to observe failures and confirm root cause analysis.

**Test Cases**:
1. **DeviceStateService Normalization Test**: Pass device version `17.15.01` to `_normalize_device_info()` → verify inline parsing produces `17.15` (will pass on unfixed code, confirms existing behavior)
2. **IngestionService Normalization Test**: Pass PDF filename with `VERSION: 17.15.01` to `_extract_metadata_from_filename()` → verify inline parsing produces `17.15` (will pass on unfixed code, confirms existing behavior)
3. **DocumentParser Missing Normalization Test**: Pass PDF content block with `VERSION: 17.15.01` to `_extract_metadata_from_block()` → verify raw value `17.15.01` is stored (will pass on unfixed code, confirms bug)
4. **RetrievalService Mismatch Test**: Query Chroma with device version `17.15` against metadata `17.15.01` → verify 0 chunks returned (will fail on unfixed code, confirms bug)
5. **End-to-End Mismatch Test**: Simulate full pipeline with device version `17.15.01` and PDF version `17.15.01` → verify retrieval returns 0 chunks due to mismatch (will fail on unfixed code, confirms bug)

**Expected Counterexamples**:
- DocumentParser stores `17.15.01` while DeviceStateService normalizes to `17.15` (MISMATCH)
- RetrievalService queries with `17.15` but Chroma metadata contains `17.15.01` (FILTER FAILURE)
- Possible causes: missing normalization in DocumentParser, missing normalization in RetrievalService, duplicated logic creates inconsistency risk

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (version processing in any component), the fixed code uses the shared `normalize_version()` utility function.

**Pseudocode:**
```
FOR ALL component IN [DeviceStateService, IngestionService, DocumentParser, RetrievalService] DO
  FOR ALL version_input IN test_versions DO
    result := component.process_version(version_input)
    ASSERT result == normalize_version(version_input)
    ASSERT component.uses_shared_utility == True
  END FOR
END FOR
```

**Test Cases**:
1. **Shared Utility Function Test**: Test `normalize_version()` with various inputs
   - `normalize_version("17.15.01")` → `"17.15"`
   - `normalize_version("17.15")` → `"17.15"`
   - `normalize_version("9.3.12")` → `"9.3"`
   - `normalize_version(None)` → `None`
   - `normalize_version("")` → `""`
   - `normalize_version("17")` → `"17"` (less than 2 components)

2. **DeviceStateService Integration Test**: Verify `_normalize_device_info()` uses shared utility
   - Mock device with version `17.15.01` → verify `info["os_version"] == "17.15"`
   - Verify no inline parsing logic remains in code

3. **IngestionService Integration Test**: Verify `_extract_metadata_from_filename()` uses shared utility
   - Mock PDF filename with `VERSION: 17.15.01` → verify `metadata["VERSION"] == "17.15"`
   - Verify no inline parsing logic remains in code

4. **DocumentParser Integration Test**: Verify `_extract_metadata_from_block()` uses shared utility
   - Mock PDF content block with `VERSION: 17.15.01` → verify `global_metadata["VERSION"] == "17.15"`
   - Verify normalization is applied before storing metadata

5. **RetrievalService Integration Test**: Verify `retrieve()` uses shared utility
   - Call `retrieve()` with version `17.15.01` → verify filter uses `"17.15"`
   - Call `retrieve()` with version `17.15` → verify filter uses `"17.15"`
   - Verify normalization is applied before building filters

6. **End-to-End Consistency Test**: Simulate full pipeline with device version `17.15.01` and PDF version `17.15.01`
   - Verify DeviceStateService normalizes to `17.15`
   - Verify DocumentParser normalizes to `17.15`
   - Verify RetrievalService normalizes query to `17.15`
   - Verify retrieval returns chunks (MATCH SUCCESS)

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (non-version metadata and filtering operations), the fixed code produces the same result as the original code.

**Pseudocode:**
```
FOR ALL operation IN [intent_filtering, collection_resolution, metadata_extraction, deduplication] DO
  FOR ALL input WHERE NOT involves_version_processing(input) DO
    ASSERT fixed_code(input) == original_code(input)
  END FOR
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain (various intents, vendors, OS versions, metadata fields)
- It catches edge cases that manual unit tests might miss (empty metadata, special characters, missing fields)
- It provides strong guarantees that behavior is unchanged for all non-version operations

**Test Plan**: Observe behavior on UNFIXED code first for non-version operations (intent filtering, collection resolution, metadata extraction), then write property-based tests capturing that behavior. Run tests on FIXED code to verify preservation.

**Test Cases**:
1. **Intent Filtering Preservation**: Verify RetrievalService continues to filter by intent fields
   - Generate random intents (access_port, create_vlan, trunk_port, etc.)
   - Query with intent filters on unfixed code → record results
   - Query with intent filters on fixed code → verify identical results
   - Verify `$or` filter logic for intent/INTENT/feature/FEATURE/topic/TOPIC remains unchanged

2. **Collection Resolution Preservation**: Verify RetrievalService continues to resolve collection names correctly
   - Generate random vendor/OS combinations (Cisco/IOS-XE, Arista/EOS, etc.)
   - Call `_resolve_collection_name()` on unfixed code → record results
   - Call `_resolve_collection_name()` on fixed code → verify identical results
   - Verify ValueError is raised for unregistered vendor/OS combinations

3. **Metadata Extraction Preservation**: Verify DocumentParser continues to extract all metadata fields
   - Generate random PDF content blocks with VENDOR, OS, INTENT, TOPIC, FEATURE metadata
   - Parse blocks on unfixed code → record extracted metadata
   - Parse blocks on fixed code → verify identical metadata (except VERSION is now normalized)
   - Verify METADATA_PATTERN regex and SUPPORTED_METADATA list remain unchanged

4. **Content Deduplication Preservation**: Verify DocumentParser continues to deduplicate content
   - Generate random PDF content with duplicate blocks
   - Parse PDF on unfixed code → record unique block count
   - Parse PDF on fixed code → verify identical unique block count
   - Verify SHA-256 hashing logic remains unchanged

5. **Device State Extraction Preservation**: Verify DeviceStateService continues to extract non-version fields
   - Generate random device state with hostname, model, serial, VLANs, interfaces
   - Normalize device info on unfixed code → record extracted fields
   - Normalize device info on fixed code → verify identical fields (except os_version is now normalized)
   - Verify hostname, model, serial, VLAN, and interface extraction logic remains unchanged

### Unit Tests

- Test `normalize_version()` with valid inputs (major.minor.patch, major.minor, single component)
- Test `normalize_version()` with edge cases (None, empty string, whitespace)
- Test DeviceStateService uses shared utility instead of inline parsing
- Test IngestionService uses shared utility instead of inline parsing
- Test DocumentParser normalizes VERSION metadata before storing
- Test RetrievalService normalizes version parameter before building filters
- Test end-to-end version consistency across all components

### Property-Based Tests

- Generate random version strings (various formats, lengths, components) and verify `normalize_version()` always returns major.minor or original
- Generate random device states and verify DeviceStateService produces consistent normalized versions
- Generate random PDF metadata and verify DocumentParser produces consistent normalized versions
- Generate random retrieval queries and verify RetrievalService produces consistent normalized filters
- Generate random non-version metadata and verify all components preserve existing behavior

### Integration Tests

- Test full RAG pipeline with device version `17.15.01` and PDF version `17.15.01` → verify retrieval succeeds
- Test full RAG pipeline with device version `9.3.12` and PDF version `9.3.12` → verify retrieval succeeds
- Test full RAG pipeline with already-normalized versions (`17.15`) → verify retrieval succeeds
- Test re-ingestion workflow: clear Chroma collections, re-ingest PDFs, verify all metadata uses normalized versions
- Test retrieval with intent filters and version filters combined → verify both filters work correctly
- Test retrieval with missing version parameter → verify intent filtering still works
