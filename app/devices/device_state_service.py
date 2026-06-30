from __future__ import annotations
import json
import logging
import time
from typing import Any, Dict, List, Optional
import requests
import urllib3
from app.devices.connection_service import ConnectionService
from app.utils.version_utils import normalize_version
from config.settings import DEVICE_TIMEOUT
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 10.0  # seconds
BACKOFF_MULTIPLIER = 2.0
RETRYABLE_STATUS_CODES = {502, 503, 504}
NON_RETRYABLE_STATUS_CODES = {401, 403, 404}


_DEFAULT_RESULT = {
    "device_info": {},
    "vlans":       [],
    "interfaces":  [],
}
class DeviceStateService:
    NORMALIZERS = {
        "device_info": "_normalize_device_info",
        "vlans":       "_normalize_vlans",
        "interfaces":  "_normalize_interfaces",
    }
    FETCH_HANDLERS = {
        "restconf":   "_fetch_restconf",
        "nxapi_rest": "_fetch_nxapi",
    }
    def __init__(self,connection_service: ConnectionService,) -> None:
        self._connection = connection_service

    def get_device_state(self,device: Dict[str, Any],state_type: str = "vlans",) -> Dict:

        try:
            connection = self._connection.connect(device)
            self._validate_connection(connection)

            method = connection["connection_method"]
            handler_name = self.FETCH_HANDLERS.get(method)

            if not handler_name:
                raise ValueError(f"Unsupported connection method: {method}")
            handler = self._get_callable(handler_name)
            requested_keys = self._select_keys(connection, state_type)

           
            result = {key: value for key, value in _DEFAULT_RESULT.items()}

            for key in requested_keys:
                raw = handler(connection, key)
                normalized = self._normalize(raw, key)
                if isinstance(normalized, dict):
                    result.update(normalized)

            result = self._build_lookup_state(result)

            logger.info("Retrieved state from %s (keys=%s)",connection["host"],requested_keys,)

            logger.info(
                "Retrieved device facts:\n%s",json.dumps(result, indent=2, default=str),)

            return result

        except Exception as exc:

            logger.exception("State retrieval failed")
            raise RuntimeError(
                f"device_state_failed: {exc}"
            ) from exc


   

    def _select_keys(self,connection: Dict,state_type: str,) -> List[str]:
      

        capability = connection.get("capability", {}) or {}
        declared = (
            capability.get("state_endpoints")
            or capability.get("state_commands")
            or {}
        )

        if state_type == "all":
            return [key for key in declared.keys() if key]

        return [state_type] if state_type else []


    def _validate_connection(self,connection: Dict,) -> None:

        required = [
            "host",
            "port",
            "connection_method",
            "username",
            "password",
            "capability",
        ]

        missing = [
            field
            for field in required
            if field not in connection or not connection[field]]

        if missing:
            raise ValueError(
                f"Invalid connection schema: {missing}"
            )


    def _get_callable(
        self,
        method_name: str,
    ):

        method = getattr(self, method_name, None)
        if not callable(method):
            raise RuntimeError(f"Invalid method: {method_name}")
        return method


    @staticmethod
    def _build_lookup_state(result: Dict) -> Dict:


        vlan_list = result.get("vlans", [])
        vlan_lookup = set()
        for v in vlan_list:
            vid = v.get("vlan_id")
            if vid is not None:
                vlan_lookup.add(vid)

        intf_list = result.get("interfaces", [])
        intf_lookup = {}
        for intf in intf_list:
            name = intf.get("name")
            if name:
                intf_lookup[name] = intf

        result["vlans"] = vlan_lookup
        result["interfaces"] = intf_lookup
        result["_raw_vlans"] = vlan_list
        result["_raw_interfaces"] = intf_list

        return result


 

    def _fetch_restconf(
        self,
        connection: Dict,
        state_type: str,
    ) -> Dict:

        endpoint = (
            connection
            .get("capability", {})
            .get("state_endpoints", {})
            .get(state_type)
        )

        if not endpoint:
            raise ValueError(
                f"No endpoint configured for {state_type}"
            )

        url = (
            f"https://{connection['host']}:"
            f"{connection['port']}{endpoint}"
        )

        return self._http_get_with_retry(
            url=url,
            auth=(connection["username"], connection["password"]),
            headers={"Accept": "application/yang-data+json"},
            operation=f"RESTCONF GET {state_type}",
            host=connection['host']
        )


    def _fetch_nxapi(self,connection: Dict,state_type: str,) -> Dict:

        command = (
            connection
            .get("capability", {})
            .get("state_commands", {})
            .get(state_type)
        )

        if not command:
            raise ValueError(
                f"No command configured for {state_type}"
            )

        payload = {
            "ins_api": {
                "version":       "1.0",
                "type":          "cli_show",
                "input":         command,
                "output_format": "json",
            }
        }

        url = (
            f"https://{connection['host']}:"
            f"{connection['port']}/ins"
        )

        return self._http_post_with_retry(
            url=url,
            auth=(connection["username"], connection["password"]),
            json_payload=payload,
            operation=f"NXAPI {state_type}",
            host=connection['host']
        )


    def _http_get_with_retry(
        self,
        url: str,
        auth: tuple,
        headers: Dict[str, str],
        operation: str,
        host: str
    ) -> Dict:
        """
        Execute HTTP GET with exponential backoff retry for transient failures.
        
        Retries on:
        - 502 Bad Gateway
        - 503 Service Unavailable
        - 504 Gateway Timeout
        - Connection timeouts
        - Connection errors
        
        Does NOT retry on:
        - 401 Unauthorized
        - 403 Forbidden
        - 404 Not Found
        """
        last_exception: Optional[Exception] = None
        backoff = INITIAL_BACKOFF
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(
                    "Attempt %d/%d: %s to %s",
                    attempt, MAX_RETRIES, operation, host
                )
                
                response = requests.get(
                    url,
                    auth=auth,
                    headers=headers,
                    verify=False,
                    timeout=DEVICE_TIMEOUT,
                )
                
                # Check for non-retryable status codes first
                if response.status_code in NON_RETRYABLE_STATUS_CODES:
                    logger.error(
                        "%s failed with non-retryable status %d: %s",
                        operation, response.status_code, response.text[:200]
                    )
                    response.raise_for_status()
                
                # Check for retryable status codes
                if response.status_code in RETRYABLE_STATUS_CODES:
                    logger.warning(
                        "%s returned transient error %d (attempt %d/%d)",
                        operation, response.status_code, attempt, MAX_RETRIES
                    )
                    
                    if attempt < MAX_RETRIES:
                        logger.info("Retrying after %.1f seconds...", backoff)
                        time.sleep(backoff)
                        backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                        continue
                    else:
                        logger.error(
                            "%s failed after %d attempts with status %d",
                            operation, MAX_RETRIES, response.status_code
                        )
                        response.raise_for_status()
                
                # Success - raise for any other HTTP errors
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(
                    "%s timed out (attempt %d/%d): %s",
                    operation, attempt, MAX_RETRIES, str(e)
                )
                
                if attempt < MAX_RETRIES:
                    logger.info("Retrying after %.1f seconds...", backoff)
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    continue
                else:
                    logger.error(
                        "%s failed after %d attempts due to timeout",
                        operation, MAX_RETRIES
                    )
                    raise
                    
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(
                    "%s connection error (attempt %d/%d): %s",
                    operation, attempt, MAX_RETRIES, str(e)
                )
                
                if attempt < MAX_RETRIES:
                    logger.info("Retrying after %.1f seconds...", backoff)
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    continue
                else:
                    logger.error(
                        "%s failed after %d attempts due to connection error",
                        operation, MAX_RETRIES
                    )
                    raise
                    
            except requests.exceptions.HTTPError as e:
                # HTTPError for non-retryable status codes - don't retry
                logger.error("%s failed with HTTP error: %s", operation, str(e))
                raise
                
            except Exception as e:
                # Unexpected errors - don't retry
                logger.exception("%s failed with unexpected error", operation)
                raise
        
        # Should not reach here, but if we do, raise the last exception
        if last_exception:
            raise last_exception
        raise RuntimeError(f"{operation} failed after {MAX_RETRIES} attempts")

    def _http_post_with_retry(
        self,
        url: str,
        auth: tuple,
        json_payload: Dict,
        operation: str,
        host: str
    ) -> Dict:
        """
        Execute HTTP POST with exponential backoff retry for transient failures.
        
        Same retry logic as _http_get_with_retry but for POST requests.
        """
        last_exception: Optional[Exception] = None
        backoff = INITIAL_BACKOFF
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(
                    "Attempt %d/%d: %s to %s",
                    attempt, MAX_RETRIES, operation, host
                )
                
                response = requests.post(
                    url,
                    auth=auth,
                    json=json_payload,
                    verify=False,
                    timeout=DEVICE_TIMEOUT,
                )
                
                # Check for non-retryable status codes first
                if response.status_code in NON_RETRYABLE_STATUS_CODES:
                    logger.error(
                        "%s failed with non-retryable status %d: %s",
                        operation, response.status_code, response.text[:200]
                    )
                    response.raise_for_status()
                
                # Check for retryable status codes
                if response.status_code in RETRYABLE_STATUS_CODES:
                    logger.warning(
                        "%s returned transient error %d (attempt %d/%d)",
                        operation, response.status_code, attempt, MAX_RETRIES
                    )
                    
                    if attempt < MAX_RETRIES:
                        logger.info("Retrying after %.1f seconds...", backoff)
                        time.sleep(backoff)
                        backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                        continue
                    else:
                        logger.error(
                            "%s failed after %d attempts with status %d",
                            operation, MAX_RETRIES, response.status_code
                        )
                        response.raise_for_status()
                
                # Success - raise for any other HTTP errors
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(
                    "%s timed out (attempt %d/%d): %s",
                    operation, attempt, MAX_RETRIES, str(e)
                )
                
                if attempt < MAX_RETRIES:
                    logger.info("Retrying after %.1f seconds...", backoff)
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    continue
                else:
                    logger.error(
                        "%s failed after %d attempts due to timeout",
                        operation, MAX_RETRIES
                    )
                    raise
                    
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(
                    "%s connection error (attempt %d/%d): %s",
                    operation, attempt, MAX_RETRIES, str(e)
                )
                
                if attempt < MAX_RETRIES:
                    logger.info("Retrying after %.1f seconds...", backoff)
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    continue
                else:
                    logger.error(
                        "%s failed after %d attempts due to connection error",
                        operation, MAX_RETRIES
                    )
                    raise
                    
            except requests.exceptions.HTTPError as e:
                # HTTPError for non-retryable status codes - don't retry
                logger.error("%s failed with HTTP error: %s", operation, str(e))
                raise
                
            except Exception as e:
                # Unexpected errors - don't retry
                logger.exception("%s failed with unexpected error", operation)
                raise
        
        # Should not reach here, but if we do, raise the last exception
        if last_exception:
            raise last_exception
        raise RuntimeError(f"{operation} failed after {MAX_RETRIES} attempts")

    def _normalize(self,raw: Dict,state_type: str,) -> Dict:

        method_name = self.NORMALIZERS.get(state_type)

        if not method_name:
            logger.warning("No normalizer for %s", state_type)
            return {}

        normalizer = self._get_callable(method_name)
        return normalizer(raw)


    @staticmethod
    def _safe_str(value: Any) -> str:
        """Coerce a value to a stripped string, or '' if not a string."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return ""


    def _normalize_device_info(self,raw: Dict,) -> Dict:

        info = {
            "hostname":   "",
            "os_version": "",
            "model":      "",
            "serial":     "",
        }

        try:
            native = raw.get("Cisco-IOS-XE-native:native", {}) or {}
            if isinstance(native, dict):
                info["hostname"] = self._safe_str(native.get("hostname"))

                # Normalize version to major.minor using shared utility
                raw_version = self._safe_str(native.get("version"))
                info["os_version"] = normalize_version(raw_version)

        except Exception:
            logger.exception("device_info normalization failed")

        return {"device_info": info}


    def _normalize_vlans(self,raw: Dict,) -> Dict:
        vlans: List[Dict[str, Any]] = []

        try:
            container = raw.get("Cisco-IOS-XE-native:vlan", {}) or {}
            vlan_items = container.get(
                "Cisco-IOS-XE-vlan:vlan-list", []
            ) or []

            for item in vlan_items:
                if not isinstance(item, dict):
                    continue

                vlan_id = item.get("id")
                try:
                    vlan_id = int(vlan_id) if vlan_id is not None else None
                except (TypeError, ValueError):
                    pass

                vlans.append({
                    "vlan_id": vlan_id,
                    "name":    self._safe_str(item.get("name")),
                })

        except Exception:
            logger.exception("VLAN normalization failed")

        return {"vlans": vlans}


    def _normalize_interfaces(self,raw: Dict,) -> Dict:
        interfaces: List[Dict[str, Any]] = []

        try:
            native_intf = raw.get("Cisco-IOS-XE-native:interface", {}) or {}

            for intf_type, items in native_intf.items():
                if not isinstance(items, list):
                    continue

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    name = f"{intf_type}{item.get('name', '')}"
                    description = self._safe_str(item.get("description"))
                    shutdown = item.get("shutdown") is not None

                    # Authoritative switchport config lives under
                    # switchport-config/switchport (writable config path).
                    # The top-level switchport key is read-only operational state.
                    switchport_config_block = item.get("switchport-config") or {}
                    switchport_cfg = switchport_config_block.get("switchport", {}) or {}

                    # Fall back to top-level switchport for devices that
                    # don't use the switchport-config wrapper.
                    if not switchport_cfg and not switchport_config_block:
                        switchport_cfg = item.get("switchport", {}) or {}

                    # Determine interface mode from the config:
                    # - "trunk"  : switchport mode trunk is configured
                    # - "access" : switchport mode access is configured, or
                    #              switchport-config is present (L2 port, default access)
                    # - "routed" : no switchport-config block at all (Layer 3 routed port)
                    has_switchport_config = bool(
                        item.get("switchport-config") or item.get("switchport")
                    )
                    mode_config = switchport_cfg.get(
                        "Cisco-IOS-XE-switch:mode", {}
                    ) or {}

                    if "trunk" in mode_config:
                        mode = "trunk"
                    elif "access" in mode_config or has_switchport_config:
                        mode = "access"
                    else:
                        # No switchport config present — this is a routed (Layer 3) port
                        mode = "routed"

                    entry: Dict[str, Any] = {
                        "name": name,
                        "description": description,
                        "mode": mode,
                        "status": "down" if shutdown else "up",
                    }

                    access_vlan = (
                        switchport_cfg
                        .get("Cisco-IOS-XE-switch:access", {})
                        .get("vlan", {})
                        .get("vlan")
                    )
                    if access_vlan is not None:
                        entry["access_vlan"] = int(access_vlan)

                    if mode == "trunk":
                        trunk_cfg = switchport_cfg.get(
                            "Cisco-IOS-XE-switch:trunk", {}
                        ) or {}

                        allowed = (
                            trunk_cfg.get("allowed", {})
                            .get("vlan", {})
                            .get("vlans", "")
                        )
                        if allowed:
                            entry["allowed_vlans"] = str(allowed)

                        native_vlan = trunk_cfg.get("native", {}).get("vlan")
                        if native_vlan is not None:
                            entry["native_vlan"] = int(native_vlan)

                    interfaces.append(entry)

        except Exception:
            logger.exception("Interface normalization failed")

        return {"interfaces": interfaces}
