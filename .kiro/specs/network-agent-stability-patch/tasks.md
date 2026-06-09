# Implementation Plan: Network Agent Stability Patch

## Overview

This implementation plan addresses four production defects in the Network Configuration Agent through minimal, behavior-preserving patches. The tasks are organized to implement fixes incrementally while maintaining the existing architecture and ensuring backward compatibility.

## Tasks

- [x] 1. Enhance settings configuration for SSL verification and timeout management
  - Add SSL_VERIFY boolean configuration from environment variable with default False
  - Ensure existing timeout configurations (OLLAMA_TIMEOUT, SERVICENOW_TIMEOUT, DEVICE_TIMEOUT) are properly exposed
  - Add environment variable parsing for SSL_VERIFY with support for multiple boolean formats
  - _Requirements: 4.1, 4.2, 4.7, 3.6_

- [ ] 2. Implement stage logging infrastructure
  - [ ] 2.1 Add stage_logger to logger utility module
    - Create dedicated Python logging.Logger instance for machine-parseable stage logs
    - Configure stage_logger with appropriate formatting and level
    - Ensure stage logging failures cannot break pipeline execution
    - _Requirements: 2.11, 2.12_
  
  - [ ]* 2.2 Write unit tests for stage logger configuration
    - Test logger initialization and configuration
    - Test error handling when logging fails
    - _Requirements: 2.11, 2.12_

- [ ] 3. Fix interface summary spacing in orchestration logger
  - [ ] 3.1 Enhance format_interface_summary method in OrchestrationLogger
    - Implement minimum one-space separation between all columns
    - Handle cases where interface names exceed column width
    - Preserve existing column order, labels, and table structure
    - Apply spacing fix to all column pairs (Interface, Status, Mode, Access VLAN, Description)
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6, 1.7_
  
  - [ ]* 3.2 Write unit tests for interface summary formatting
    - Test spacing with normal-length interface names
    - Test spacing with interface names that exceed column width
    - Test handling of missing/null interface fields
    - _Requirements: 1.1, 1.2, 1.7_

- [ ] 4. Fix table formatting in display service
  - [ ] 4.1 Enhance _format_row function in display_service.py
    - Ensure minimum one space between columns even when values exceed width
    - Apply same spacing rules as orchestration logger
    - Preserve existing table structure and formatting
    - _Requirements: 1.4_
  
  - [ ]* 4.2 Write unit tests for display service table formatting
    - Test _format_row with various value lengths and widths
    - Test preservation of existing table structure
    - _Requirements: 1.4_

- [ ] 5. Add comprehensive stage logging to orchestrator service
  - [ ] 5.1 Add entry/exit logging to orchestrator pipeline stages
    - Add "Entering" logs before each stage begins
    - Add "Completed" logs when stages finish successfully
    - Add "Failed" logs when stages raise exceptions
    - Cover all major stages: Intent Extraction, Schema Validation, Workflow Validation, CMDB Lookup, Device Facts, State Validation
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [ ] 5.2 Add detailed logging to payload generation service
    - Add "Entering retrieval stage" before ChromaDB query
    - Add "Retrieval completed" after ChromaDB query returns
    - Add "Starting LLM inference" before Ollama chat call
    - Add "LLM inference completed" after Ollama response received
    - Add "Payload generation completed" after JSON parsing/validation
    - _Requirements: 2.5, 2.6, 2.7_
  
  - [ ] 5.3 Add logging to execution stages
    - Add entry/exit logs for push configuration operations
    - Add entry/exit logs for execution verification operations
    - Handle skipped stages with "Skipped" logs and reasons
    - _Requirements: 2.8, 2.9, 2.10_
  
  - [ ]* 5.4 Write integration tests for stage logging
    - Test complete pipeline execution produces expected log sequence
    - Test error scenarios produce appropriate "Failed" logs
    - Test skipped stages produce "Skipped" logs
    - _Requirements: 2.1, 2.2, 2.3, 2.10_

- [ ] 6. Checkpoint - Verify logging and formatting improvements
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement timeout configuration for external calls
  - [ ] 7.1 Add timeout handling to Ollama client
    - Ensure OllamaClient uses OLLAMA_TIMEOUT configuration
    - Apply timeout to underlying HTTP transport via httpx.Timeout
    - Convert timeout exceptions to structured error results
    - _Requirements: 3.2, 3.8, 3.9_
  
  - [ ] 7.2 Add timeout handling to Intent Service
    - Apply OLLAMA_TIMEOUT to Intent Service Ollama calls
    - Convert timeout exceptions to structured error results
    - _Requirements: 3.3, 3.8, 3.9_
  
  - [ ] 7.3 Add timeout handling to Retrieval Service
    - Add timeout configuration for ChromaDB queries
    - Wrap queries to detect stuck retrieval operations
    - Convert timeout exceptions to structured error results
    - _Requirements: 3.5, 3.8, 3.9_
  
  - [ ]* 7.4 Write unit tests for timeout handling
    - Test timeout configuration is properly applied
    - Test timeout exceptions are converted to structured errors
    - Test existing timeout values are preserved
    - _Requirements: 3.7, 3.8, 3.9, 3.11_

- [ ] 8. Implement configurable SSL verification for device calls
  - [ ] 8.1 Update device connection services to use SSL_VERIFY setting
    - Modify PushConfigExecutor to use verify=SSL_VERIFY instead of verify=False
    - Modify ExecutionStatusVerifier to use verify=SSL_VERIFY
    - Modify DeviceStateService to use verify=SSL_VERIFY
    - Ensure ServiceNow calls continue using requests default (verify=True)
    - _Requirements: 4.3, 4.4, 4.8_
  
  - [ ] 8.2 Add SSL warning suppression for sandbox mode
    - Suppress urllib3.exceptions.InsecureRequestWarning when SSL_VERIFY=False
    - Allow warnings when SSL_VERIFY=True
    - Implement suppression once at startup
    - _Requirements: 4.5, 4.6_
  
  - [ ] 8.3 Update environment configuration documentation
    - Document SSL_VERIFY in .env file with default value
    - Ensure no real credentials are committed to repository
    - _Requirements: 4.9_
  
  - [ ]* 8.4 Write unit tests for SSL verification configuration
    - Test SSL_VERIFY environment variable parsing
    - Test device calls use correct verify parameter
    - Test ServiceNow calls remain unchanged
    - _Requirements: 4.2, 4.3, 4.7, 4.8_

- [ ] 9. Final integration and compatibility verification
  - [ ] 9.1 Verify backward compatibility of outputs
    - Ensure Display_Service produces same final orchestration result (except spacing fixes)
    - Verify existing stage banners are preserved
    - Verify JSON structure returned by orchestrator_service.process_task is unchanged
    - Verify no InsecureRequestWarning appears in sandbox mode
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [ ] 9.2 Verify architecture preservation constraints
    - Confirm no new top-level folders added
    - Confirm no existing files deleted, renamed, or relocated
    - Confirm pipeline order preserved exactly
    - Confirm public method signatures unchanged
    - Confirm minimal diff approach maintained
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.9, 5.10_
  
  - [ ]* 9.3 Write end-to-end integration tests
    - Test complete pipeline execution with all patches applied
    - Test error scenarios and timeout handling
    - Test SSL verification in both modes
    - _Requirements: 3.1, 4.1, 6.1_

- [ ] 10. Final checkpoint - Ensure all tests pass and requirements met
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- All changes maintain backward compatibility and preserve existing architecture
- Focus on minimal, behavior-preserving patches that fix production defects
- SSL verification defaults to False (sandbox mode) to preserve current behavior
- Timeout values use existing configuration patterns and defaults