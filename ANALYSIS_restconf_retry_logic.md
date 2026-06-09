# Analysis: RESTCONF Retry Logic for Transient Failures

## Problem Identified

DeviceStateService was failing immediately on transient RESTCONF errors without retry attempts.

### Observed Error

```
GET /restconf/data/Cisco-IOS-XE-native:native
HTTP 502 Bad Gateway
```

The failure occurred before state retrieval completed, causing workflow failures for transient network issues.

## Root Cause Analysis

### Current Implementation (Before Fix)

```python
def _fetch_restconf(self, connection: Dict, state_type: str) -> Dict:
    response = requests.get(url, auth=auth, headers=headers, verify=False, timeout=DEVICE_TIMEOUT)
    response.raise_for_status()  # ❌ Fails immediately on any HTTP error
    return response.json()
```

**Issues:**
1. No retry logic for transient failures
2. All HTTP errors treated equally (502 same as 401)
3. Connection timeouts fail immediately
4. No exponential backoff

### Potential Error Sources

1. **Sandbox Gateway**: Proxy/load balancer returning 502
2. **IOS-XE Backend**: RESTCONF service temporarily unavailable
3. **Network**: Transient connectivity issues
4. **Application Code**: No - verified requests library usage is correct

## Solution Implemented

### Retry Logic with Exponential Backoff

Implemented two new methods in `DeviceStateService`:
- `_http_get_with_retry()` - For RESTCONF GET requests
- `_http_post_with_retry()` - For NXAPI POST requests

### Configuration

```python
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 10.0  # seconds
BACKOFF_MULTIPLIER = 2.0

# Retryable status codes
RETRYABLE_STATUS_CODES = {502, 503, 504}

# Non-retryable status codes
NON_RETRYABLE_STATUS_CODES = {401, 403, 404}
```

### Retry Decision Matrix

| Error Type | Status Code | Action | Rationale |
|------------|-------------|--------|-----------|
| Bad Gateway | 502 | ✅ Retry | Transient gateway/proxy issue |
| Service Unavailable | 503 | ✅ Retry | Backend temporarily down |
| Gateway Timeout | 504 | ✅ Retry | Backend response timeout |
| Connection Timeout | N/A | ✅ Retry | Network latency |
| Connection Error | N/A | ✅ Retry | Network connectivity |
| Unauthorized | 401 | ❌ No Retry | Credentials issue |
| Forbidden | 403 | ❌ No Retry | Authorization issue |
| Not Found | 404 | ❌ No Retry | Endpoint doesn't exist |

### Exponential Backoff

```
Attempt 1: Immediate
Attempt 2: Wait 1.0s
Attempt 3: Wait 2.0s
Attempt 4: Wait 4.0s (if MAX_RETRIES increased)
```

Maximum backoff capped at 10 seconds to prevent excessive delays.

### Implementation Details

```python
def _http_get_with_retry(self, url, auth, headers, operation, host) -> Dict:
    last_exception = None
    backoff = INITIAL_BACKOFF
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, auth=auth, headers=headers, 
                                   verify=False, timeout=DEVICE_TIMEOUT)
            
            # Check for non-retryable status codes first
            if response.status_code in NON_RETRYABLE_STATUS_CODES:
                logger.error("Non-retryable status %d", response.status_code)
                response.raise_for_status()
            
            # Check for retryable status codes
            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt < MAX_RETRIES:
                    logger.info("Retrying after %.1f seconds...", backoff)
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    continue
                else:
                    response.raise_for_status()
            
            # Success
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout as e:
            # Retry on timeout
            if attempt < MAX_RETRIES:
                time.sleep(backoff)
                backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                continue
            raise
            
        except requests.exceptions.ConnectionError as e:
            # Retry on connection error
            if attempt < MAX_RETRIES:
                time.sleep(backoff)
                backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                continue
            raise
            
        except requests.exceptions.HTTPError as e:
            # Non-retryable HTTP errors - don't retry
            raise
```

## Logging

Enhanced logging for troubleshooting:

```python
# Attempt logging
logger.debug("Attempt %d/%d: %s to %s", attempt, MAX_RETRIES, operation, host)

# Transient error logging
logger.warning("%s returned transient error %d (attempt %d/%d)", 
               operation, response.status_code, attempt, MAX_RETRIES)

# Retry logging
logger.info("Retrying after %.1f seconds...", backoff)

# Non-retryable error logging
logger.error("%s failed with non-retryable status %d: %s",
             operation, response.status_code, response.text[:200])
```

## Benefits

1. ✅ **Resilience**: Transient failures automatically retried
2. ✅ **Smart Retry**: Only retries appropriate errors
3. ✅ **Exponential Backoff**: Prevents overwhelming backend
4. ✅ **Preserves Contracts**: No changes to method signatures
5. ✅ **Vendor-Agnostic**: No sandbox-specific hardcoding
6. ✅ **Comprehensive Logging**: Easy troubleshooting

## Files Modified

### app/devices/device_state_service.py

**Added:**
- Retry configuration constants
- `_http_get_with_retry()` method
- `_http_post_with_retry()` method

**Modified:**
- `_fetch_restconf()` - Now uses `_http_get_with_retry()`
- `_fetch_nxapi()` - Now uses `_http_post_with_retry()`

**No Changes:**
- Connection contracts preserved
- Normalization logic unchanged
- Orchestrator integration unchanged

## Validation

### Test Script: test_restconf_connectivity.py

Tests:
1. Direct RESTCONF endpoint reachability
2. DeviceStateService retry logic
3. Error classification (retryable vs non-retryable)
4. VLAN state retrieval
5. Interface state retrieval
6. Complete state retrieval

### Expected Behavior

**Scenario 1: Transient 502 Error**
```
Attempt 1: 502 Bad Gateway
  → Wait 1.0s
Attempt 2: 502 Bad Gateway
  → Wait 2.0s
Attempt 3: 200 OK
  → Success
```

**Scenario 2: Persistent 502 Error**
```
Attempt 1: 502 Bad Gateway
  → Wait 1.0s
Attempt 2: 502 Bad Gateway
  → Wait 2.0s
Attempt 3: 502 Bad Gateway
  → Fail with HTTPError
```

**Scenario 3: 401 Unauthorized**
```
Attempt 1: 401 Unauthorized
  → Fail immediately (no retry)
```

**Scenario 4: Connection Timeout**
```
Attempt 1: Timeout
  → Wait 1.0s
Attempt 2: Timeout
  → Wait 2.0s
Attempt 3: 200 OK
  → Success
```

## Testing with Uvicorn

### Start the Application

```bash
cd "c:\Users\Jesintha\Documents\Internal - Copy"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Test Intent Processing

```bash
# Test with a simple intent
curl -X POST http://localhost:8000/api/intent \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Create VLAN 100 on switch",
    "device_id": "switch-001"
  }'
```

### Monitor Logs

Watch for retry attempts in the logs:
```
DEBUG: Attempt 1/3: RESTCONF GET device_info to sandbox-iosxe-latest-1.cisco.com
WARNING: RESTCONF GET device_info returned transient error 502 (attempt 1/3)
INFO: Retrying after 1.0 seconds...
DEBUG: Attempt 2/3: RESTCONF GET device_info to sandbox-iosxe-latest-1.cisco.com
```

## Design Principles Followed

1. ✅ **No Sandbox-Specific Behavior**: Generic retry logic works for any RESTCONF/NXAPI endpoint
2. ✅ **Preserve Existing Contracts**: No changes to method signatures or return types
3. ✅ **Do Not Modify Orchestrator**: All changes contained in DeviceStateService
4. ✅ **Smart Error Classification**: Distinguishes transient from permanent errors
5. ✅ **Exponential Backoff**: Industry-standard retry pattern
6. ✅ **Comprehensive Logging**: Enables troubleshooting without code changes

## Future Enhancements

### Configurable Retry Parameters

Could be moved to settings.py:
```python
RESTCONF_MAX_RETRIES = get_env("RESTCONF_MAX_RETRIES", 3, int)
RESTCONF_INITIAL_BACKOFF = get_env("RESTCONF_INITIAL_BACKOFF", 1.0, float)
RESTCONF_MAX_BACKOFF = get_env("RESTCONF_MAX_BACKOFF", 10.0, float)
```

### Circuit Breaker Pattern

For persistent failures, could implement circuit breaker to fail fast:
```python
if consecutive_failures > CIRCUIT_BREAKER_THRESHOLD:
    raise CircuitBreakerOpen("RESTCONF endpoint unavailable")
```

### Metrics Collection

Track retry statistics:
```python
metrics = {
    "total_requests": 0,
    "retried_requests": 0,
    "failed_requests": 0,
    "avg_retry_count": 0.0
}
```

## Conclusion

The retry logic implementation provides robust handling of transient RESTCONF failures while maintaining clean separation of concerns and preserving existing contracts. The solution is vendor-agnostic, well-logged, and follows industry-standard retry patterns with exponential backoff.
