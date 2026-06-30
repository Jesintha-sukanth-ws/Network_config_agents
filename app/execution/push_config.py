"""
Push Config — pushes generated payloads to target devices via RESTCONF or NX-API.

Responsibilities:
- Accept validated payloads
- Establish device connection using connection_service
- Push configuration based on operation type
- Handle protocol-specific payload formatting
- Return execution status

All YANG module names, container paths, and write endpoints are read from
device_capabilities.json via connection_data["capability"]. Nothing is
hardcoded in this module.
"""

from __future__ import annotations

import logging
import re
import requests
from typing import Dict, Tuple

from app.devices.connection_service import ConnectionService
from app.utils.logger import orchestrator_logger

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def build_connection(device: Dict) -> Dict:
    """Module-level shim — preserves legacy call sites."""
    return ConnectionService().connect(device)


class PushConfigExecutor:
    """
    Executes configuration push operations on network devices.

    Supports:
    - RESTCONF (Cisco IOS-XE, Arista EOS, Juniper JunOS)
    - NX-API (Cisco NX-OS)
    """

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_interface_family(interface_name: str) -> Tuple[str, str]:
        """
        Split a Cisco interface name into its YANG family and identifier.

        Examples:
            GigabitEthernet1/0/5    -> ("GigabitEthernet", "1/0/5")
            TenGigabitEthernet1/0/1 -> ("TenGigabitEthernet", "1/0/1")
            Gi1/0/3                 -> ("GigabitEthernet", "1/0/3")
        """
        ABBREVIATIONS = {
            "Gi":  "GigabitEthernet",
            "Gig": "GigabitEthernet",
            "Te":  "TenGigabitEthernet",
            "Twe": "TwentyFiveGigE",
            "Fo":  "FortyGigabitEthernet",
            "Hu":  "HundredGigE",
            "Lo":  "Loopback",
            "Po":  "Port-channel",
            "Vl":  "Vlan",
            "Tu":  "Tunnel",
        }

        if not isinstance(interface_name, str) or not interface_name:
            raise ValueError(f"Invalid interface format: {interface_name!r}")

        match = re.match(r"([A-Za-z\-]+)(.+)", interface_name.strip())
        if not match:
            raise ValueError(f"Invalid interface format: {interface_name}")

        family     = ABBREVIATIONS.get(match.group(1), match.group(1))
        identifier = match.group(2)
        return family, identifier

    @staticmethod
    def _get_yang_schema(capability: Dict) -> Dict:
        """
        Extract YANG module names and structural paths from device capability.

        All YANG module prefixes and container names come from
        device_capabilities.json — nothing is hardcoded in push logic.

        Returns:
            native_module:  e.g. "Cisco-IOS-XE-native"
            vlan_module:    e.g. "Cisco-IOS-XE-vlan"
            switch_module:  e.g. "Cisco-IOS-XE-switch"
            sp_container:   writable switchport container, e.g. "switchport-config"
            vlan_endpoint:  full write path for VLANs
            intf_endpoint:  full write path for interfaces
        """
        modules   = capability.get("yang_modules", {})
        write_eps = capability.get("write_endpoints", {})

        native_module = modules.get("native", "")
        vlan_module   = modules.get("vlan", "")
        switch_module = modules.get("switchport", "")
        sp_container  = capability.get("switchport_config_container", "")

        if not native_module or not vlan_module or not switch_module:
            raise ValueError(
                "Device capability is missing required yang_modules "
                "(native, vlan, switchport). "
                "Update device_capabilities.json for this vendor/OS."
            )

        if not sp_container:
            raise ValueError(
                "Device capability is missing switchport_config_container. "
                "Update device_capabilities.json for this vendor/OS."
            )

        vlan_endpoint = write_eps.get("vlan", "")
        intf_endpoint = write_eps.get("interface", "")

        if not vlan_endpoint or not intf_endpoint:
            raise ValueError(
                "Device capability is missing required write_endpoints "
                "(vlan, interface). "
                "Update device_capabilities.json for this vendor/OS."
            )

        return {
            "native_module": native_module,
            "vlan_module":   vlan_module,
            "switch_module": switch_module,
            "sp_container":  sp_container,
            "vlan_endpoint": vlan_endpoint,
            "intf_endpoint": intf_endpoint,
        }

    # ─────────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────────

    def execute(self, payload: Dict, device: Dict) -> Dict:
        """
        Execute configuration push to device.

        Args:
            payload:  {"operation": str, "payload": dict}
            device:   {"device_name": str, "vendor": str, "os_type": str, ...}

        Returns:
            {"success": bool, "operation": str, "device": str, "message": str, "details": dict}
        """
        operation      = payload.get("operation")
        config_payload = payload.get("payload", {})

        logger.info(
            "Executing push config (operation=%s, device=%s, vendor=%s, os=%s)",
            operation, device.get("device_name"),
            device.get("vendor"), device.get("os_type"),
        )

        try:
            connection_data = build_connection(device)
            protocol        = connection_data["connection_method"]

            if protocol == "restconf":
                result = self._push_restconf(connection_data, operation, config_payload)
            elif protocol == "nxapi_rest":
                result = self._push_nxapi(connection_data, operation, config_payload)
            else:
                raise ValueError(f"Unsupported protocol: {protocol}")

            logger.info(
                "Push config completed (operation=%s, device=%s)",
                operation, device.get("device_name"),
            )

            return {
                "success":   True,
                "operation": operation,
                "device":    device.get("device_name"),
                "message":   f"Configuration pushed successfully via {protocol}",
                "details":   result,
            }

        except Exception as exc:
            logger.exception(
                "Push config failed (operation=%s, device=%s): %s",
                operation, device.get("device_name"), exc,
            )
            return {
                "success":   False,
                "operation": operation,
                "device":    device.get("device_name"),
                "message":   f"Configuration push failed: {str(exc)}",
                "details":   {"error": str(exc)},
            }

    # ─────────────────────────────────────────────────────────────
    # RESTCONF dispatch
    # ─────────────────────────────────────────────────────────────

    def _push_restconf(self, connection_data: Dict, operation: str, config_payload: Dict) -> Dict:

        capability = connection_data.get("capability", {})
        base_url   = f"https://{connection_data['host']}:{connection_data['port']}"
        headers    = {
            "Accept":       "application/yang-data+json",
            "Content-Type": "application/yang-data+json",
        }

        dispatch = {
            "create_vlan":                  self._restconf_create_vlan,
            "delete_vlan":                  self._restconf_delete_vlan,
            "configure_access_port":        self._restconf_access_port,
            "configure_trunk_port":         self._restconf_trunk_port,
            "configure_interface_status":   self._restconf_interface_mode,
        }

        handler = dispatch.get(operation)
        if not handler:
            raise ValueError(f"Unsupported operation: {operation}")

        return handler(base_url, headers, connection_data, config_payload, capability)

    # ─────────────────────────────────────────────────────────────
    # RESTCONF operations — all YANG details from capability
    # ─────────────────────────────────────────────────────────────

    def _restconf_create_vlan(
        self,
        base_url: str,
        headers: Dict,
        connection_data: Dict,
        config_payload: Dict,
        capability: Dict,
    ) -> Dict:
        """Create VLAN. YANG module names and endpoint from capability."""

        schema   = self._get_yang_schema(capability)
        vlan_id  = config_payload.get("vlan_id") or config_payload.get("vlan-id")
        vlan_name = (
            config_payload.get("vlan_name")
            or config_payload.get("name")
            or f"VLAN_{vlan_id}"
        )

        if vlan_id is None:
            raise ValueError(f"Missing vlan_id in payload: {config_payload}")

        vlan_id = int(vlan_id)
        url     = base_url + schema["vlan_endpoint"]

        payload = {
            f"{schema['native_module']}:vlan": {
                f"{schema['vlan_module']}:vlan-list": [
                    {"id": vlan_id, "name": vlan_name}
                ]
            }
        }

        orchestrator_logger.kv_block(
            "      DEVICE REQUEST (RESTCONF: create_vlan)",
            {"method": "PATCH", "url": url, "payload": payload},
        )

        response = requests.patch(
            url,
            auth=(connection_data["username"], connection_data["password"]),
            headers=headers, json=payload, verify=False, timeout=30,
        )

        orchestrator_logger.kv_block(
            "      DEVICE RESPONSE",
            {"status_code": response.status_code, "body": (response.text or "").strip()[:600]},
        )

        response.raise_for_status()
        return {"status_code": response.status_code, "vlan_id": vlan_id, "vlan_name": vlan_name}

    def _restconf_delete_vlan(
        self,
        base_url: str,
        headers: Dict,
        connection_data: Dict,
        config_payload: Dict,
        capability: Dict,
    ) -> Dict:

        schema  = self._get_yang_schema(capability)
        vlan_id = int(config_payload.get("vlan_id") or config_payload.get("vlan-id"))

        endpoint = (
            f"{base_url}{schema['vlan_endpoint']}/"
            f"{schema['vlan_module']}:vlan-list={vlan_id}"
        )

        orchestrator_logger.kv_block(
            "      DEVICE REQUEST (RESTCONF: delete_vlan)",
            {"method": "DELETE", "url": endpoint},
        )

        response = requests.delete(
            endpoint,
            auth=(connection_data["username"], connection_data["password"]),
            headers=headers, verify=False, timeout=30,
        )

        orchestrator_logger.kv_block(
            "      DEVICE RESPONSE",
            {"status_code": response.status_code, "body": (response.text or "").strip()[:600]},
        )

        response.raise_for_status()
        return {"status_code": response.status_code, "vlan_id": vlan_id, "message": "VLAN deleted successfully"}

    def _restconf_access_port(
        self,
        base_url: str,
        headers: Dict,
        connection_data: Dict,
        config_payload: Dict,
        capability: Dict,
    ) -> Dict:
        

        schema = self._get_yang_schema(capability)

        # Extract interface and vlan_id from flat payload
        interface_name = config_payload.get("interface")
        vlan_id = config_payload.get("vlan_id")

        if not interface_name:
            raise ValueError(f"Missing interface in payload: {config_payload}")
        if vlan_id is None:
            raise ValueError(f"Missing vlan_id in payload: {config_payload}")

        vlan_id    = int(vlan_id)
        family, identifier = self._extract_interface_family(interface_name)
        encoded_id = identifier.replace("/", "%2F")
        endpoint   = f"{base_url}{schema['intf_endpoint']}/{family}={encoded_id}"

        sw = schema["switch_module"]
        sp = schema["sp_container"]
        enable_payload = {
            f"{schema['native_module']}:{family}": {
                "name": identifier,
                sp: {
                    "switchport": {}
                }
            }
        }

        orchestrator_logger.kv_block(
            "      DEVICE REQUEST (RESTCONF: access_port — step 1: enable switchport)",
            {"method": "PATCH", "url": endpoint, "payload": enable_payload},
        )

        enable_response = requests.patch(
            endpoint,
            auth=(connection_data["username"], connection_data["password"]),
            headers=headers, json=enable_payload, verify=False, timeout=30,
        )

        orchestrator_logger.kv_block(
            "      DEVICE RESPONSE (step 1)",
            {"status_code": enable_response.status_code, "body": (enable_response.text or "").strip()[:600]},
        )

        enable_response.raise_for_status()

        # Step 2: Set mode=access and assign the VLAN.
        payload = {
            f"{schema['native_module']}:{family}": {
                "name": identifier,
                sp: {
                    "switchport": {
                        f"{sw}:mode":   {"access": {}},
                        f"{sw}:access": {"vlan": {"vlan": vlan_id}},
                    }
                }
            }
        }

        orchestrator_logger.kv_block(
            "      DEVICE REQUEST (RESTCONF: access_port — step 2: set mode + vlan)",
            {"method": "PATCH", "url": endpoint, "payload": payload},
        )

        response = requests.patch(
            endpoint,
            auth=(connection_data["username"], connection_data["password"]),
            headers=headers, json=payload, verify=False, timeout=30,
        )

        orchestrator_logger.kv_block(
            "      DEVICE RESPONSE (step 2)",
            {"status_code": response.status_code, "body": (response.text or "").strip()[:600]},
        )

        response.raise_for_status()
        return {"status_code": response.status_code, "interface": f"{family}{identifier}", "vlan_id": vlan_id, "mode": "access"}

    def _restconf_trunk_port(
        self,
        base_url: str,
        headers: Dict,
        connection_data: Dict,
        config_payload: Dict,
        capability: Dict,
    ) -> Dict:
        """Configure trunk port. All YANG details from capability."""

        schema = self._get_yang_schema(capability)

        interface_name = config_payload.get("interface")
        allowed_vlans  = config_payload.get("allowed_vlans", [])
        native_vlan    = config_payload.get("native_vlan", 1)

        family, identifier = self._extract_interface_family(interface_name)
        encoded_id = identifier.replace("/", "%2F")
        endpoint   = f"{base_url}{schema['intf_endpoint']}/{family}={encoded_id}"

        allowed_vlans_str = ",".join(str(v) for v in allowed_vlans)
        sw = schema["switch_module"]
        sp = schema["sp_container"]

        payload = {
            f"{schema['native_module']}:{family}": {
                "name": identifier,
                sp: {
                    "switchport": {
                        f"{sw}:mode":  {"trunk": {}},
                        f"{sw}:trunk": {
                            "native":  {"vlan": int(native_vlan)},
                            "allowed": {"vlan": {"vlans": allowed_vlans_str}},
                        },
                    }
                }
            }
        }

        orchestrator_logger.kv_block(
            "      DEVICE REQUEST (RESTCONF: trunk_port)",
            {"method": "PATCH", "url": endpoint, "payload": payload},
        )

        response = requests.patch(
            endpoint,
            auth=(connection_data["username"], connection_data["password"]),
            headers=headers, json=payload, verify=False, timeout=30,
        )

        orchestrator_logger.kv_block(
            "      DEVICE RESPONSE",
            {"status_code": response.status_code, "body": (response.text or "").strip()[:600]},
        )

        response.raise_for_status()
        return {"status_code": response.status_code, "interface": f"{family}{identifier}", "allowed_vlans": allowed_vlans, "native_vlan": native_vlan, "mode": "trunk"}

    def _restconf_interface_mode(
        self,
        base_url: str,
        headers: Dict,
        connection_data: Dict,
        config_payload: Dict,
        capability: Dict,
    ) -> Dict:
        """Configure interface administrative state (shutdown / no shutdown).

        Maps to the configure_interface_status intent.
        administrative_state=UP  → remove shutdown leaf (no shutdown)
        administrative_state=DOWN → add shutdown leaf (shutdown)

        YANG path: native/interface/{family}={id}/shutdown
        - To bring UP:   DELETE the shutdown leaf
        - To bring DOWN: PATCH with shutdown: [null]
        """

        schema = self._get_yang_schema(capability)

        interface_name = config_payload.get("interface")
        # Accept both "administrative_state" (from intent) and "state" (from LLM payload)
        admin_state = (
            config_payload.get("administrative_state")
            or config_payload.get("state")
            or ""
        ).upper()

        if not interface_name:
            raise ValueError(f"Missing interface in payload: {config_payload}")
        if admin_state not in ("UP", "DOWN"):
            raise ValueError(
                f"Invalid administrative_state '{admin_state}'. Must be UP or DOWN."
            )

        family, identifier = self._extract_interface_family(interface_name)
        encoded_id = identifier.replace("/", "%2F")
        intf_endpoint = f"{base_url}{schema['intf_endpoint']}/{family}={encoded_id}"

        if admin_state == "UP":
            # Remove the shutdown leaf — equivalent to "no shutdown"
            shutdown_endpoint = f"{intf_endpoint}/{schema['native_module']}:shutdown"

            orchestrator_logger.kv_block(
                "      DEVICE REQUEST (RESTCONF: interface_status — no shutdown)",
                {"method": "DELETE", "url": shutdown_endpoint},
            )

            response = requests.delete(
                shutdown_endpoint,
                auth=(connection_data["username"], connection_data["password"]),
                headers=headers, verify=False, timeout=30,
            )

        else:
            # Add the shutdown leaf — equivalent to "shutdown"
            payload = {
                f"{schema['native_module']}:{family}": {
                    "name": identifier,
                    "shutdown": [None],
                }
            }

            orchestrator_logger.kv_block(
                "      DEVICE REQUEST (RESTCONF: interface_status — shutdown)",
                {"method": "PATCH", "url": intf_endpoint, "payload": payload},
            )

            response = requests.patch(
                intf_endpoint,
                auth=(connection_data["username"], connection_data["password"]),
                headers=headers, json=payload, verify=False, timeout=30,
            )

        orchestrator_logger.kv_block(
            "      DEVICE RESPONSE",
            {"status_code": response.status_code, "body": (response.text or "").strip()[:600]},
        )

        # 404 on DELETE means shutdown leaf didn't exist — interface was already up
        if admin_state == "UP" and response.status_code == 404:
            return {
                "status_code": response.status_code,
                "interface": f"{family}{identifier}",
                "administrative_state": "UP",
                "message": "Interface was already up (no shutdown leaf present)",
            }

        response.raise_for_status()
        return {
            "status_code": response.status_code,
            "interface": f"{family}{identifier}",
            "administrative_state": admin_state,
        }

    # ─────────────────────────────────────────────────────────────
    # NX-API Push
    # ─────────────────────────────────────────────────────────────

    def _push_nxapi(self, connection_data: Dict, operation: str, config_payload: Dict) -> Dict:
        """Push configuration via NX-API (Cisco NX-OS)."""

        url          = f"https://{connection_data['host']}:{connection_data['port']}/ins"
        cli_commands = self._operation_to_cli(operation, config_payload)

        payload = {
            "ins_api": {
                "version":       "1.0",
                "type":          "cli_conf",
                "chunk":         "0",
                "sid":           "1",
                "input":         ";".join(cli_commands),
                "output_format": "json",
            }
        }

        orchestrator_logger.kv_block(
            f"      DEVICE REQUEST (NX-API: {operation})",
            {"method": "POST", "url": url, "payload": payload},
        )

        response = requests.post(
            url,
            auth=(connection_data["username"], connection_data["password"]),
            headers={"Content-Type": "application/json"},
            json=payload, verify=False, timeout=30,
        )

        orchestrator_logger.kv_block(
            "      DEVICE RESPONSE",
            {"status_code": response.status_code, "body": (response.text or "").strip()[:600]},
        )

        response.raise_for_status()
        return response.json()

    @staticmethod
    def _operation_to_cli(operation: str, config_payload: Dict) -> list:
        """Convert operation to NX-OS CLI commands."""

        if operation == "create_vlan":
            vlan_id   = config_payload.get("vlan_id")
            vlan_name = config_payload.get("vlan_name", f"VLAN_{vlan_id}")
            return [f"vlan {vlan_id}", f"name {vlan_name}"]

        elif operation == "delete_vlan":
            return [f"no vlan {config_payload.get('vlan_id')}"]

        elif operation == "configure_access_port":
            interface = config_payload.get("interface")
            vlan_id   = config_payload.get("vlan_id")
            return [
                f"interface {interface}",
                "switchport mode access",
                f"switchport access vlan {vlan_id}",
            ]

        elif operation == "configure_trunk_port":
            interface    = config_payload.get("interface")
            allowed_vlans = config_payload.get("allowed_vlans", [])
            native_vlan  = config_payload.get("native_vlan", 1)
            allowed_str  = ",".join(str(v) for v in allowed_vlans)
            return [
                f"interface {interface}",
                "switchport mode trunk",
                f"switchport trunk allowed vlan {allowed_str}",
                f"switchport trunk native vlan {native_vlan}",
            ]

        elif operation == "configure_interface_status":
            interface   = config_payload.get("interface")
            admin_state = (
                config_payload.get("administrative_state")
                or config_payload.get("state")
                or ""
            ).upper()
            if admin_state == "UP":
                return [f"interface {interface}", "no shutdown"]
            elif admin_state == "DOWN":
                return [f"interface {interface}", "shutdown"]
            return [f"interface {interface}"]

        return []
