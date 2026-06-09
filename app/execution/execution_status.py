"""
Execution Status

Responsibilities:
- Retrieve current device state
- Verify push operation results
- Compare expected vs actual state
- Return evidence
"""

from __future__ import annotations

import logging
from typing import Dict, Callable

from app.devices.connection_service import ConnectionService
from app.devices.device_state_service import DeviceStateService
from app.registry.intent_registry import CANONICAL_INTENT_SCHEMAS


logger = logging.getLogger(__name__)


def get_device_facts(
    device: Dict
) -> Dict:
    """
    Create fresh service instances to avoid state pollution between requests.
    """
    connection_service = ConnectionService()
    device_service = DeviceStateService(connection_service)
    
    return device_service.get_device_state(
        device=device,
        state_type="all"
    )


class ExecutionStatusVerifier:

    def __init__(self):
        # Create fresh service instances per verifier to avoid state pollution
        self._connection_service = ConnectionService()
        self._device_service = DeviceStateService(self._connection_service)

        # Use canonical operation names to match the operation field in payloads
        # This ensures consistency across the entire pipeline
        self._handlers = {
            "create_vlan": self._verify_vlan_creation,
            "delete_vlan": self._verify_vlan_deletion,
            "configure_access_port": self._verify_access_port,
            "configure_trunk_port": self._verify_trunk_port,
            "configure_interface_status": self._verify_interface_mode
        }

    def verify(
        self,
        push_result: Dict,
        device: Dict,
        original_payload: Dict
    ) -> Dict:

        operation = original_payload.get(
            "operation"
        )

        payload = original_payload.get(
            "payload",
            {}
        )

        logger.info(

            "Verifying execution status "
            "(operation=%s device=%s)",

            operation,
            device.get(
                "device_name"
            )
        )

        if not push_result.get(
            "success"
        ):

            return {

                "verified": False,

                "operation": operation,

                "device":
                device.get(
                    "device_name"
                ),

                "push_success": False,

                "state_verified": False,

                "message":
                "Configuration push failed",

                "expected_state": {},

                "actual_state": {},

                "evidence": {

                    "push_error":
                    push_result.get(
                        "message"
                    )
                }
            }

        try:

            device_facts = self._device_service.get_device_state(
                device=device,
                state_type="all"
            )

            handler = self._handlers.get(
                operation
            )

            if not handler:

                raise ValueError(

                    f"Unsupported operation: "
                    f"{operation}"
                )

            verified,evidence = handler(

                device_facts,
                payload
            )

            return {

                "verified":
                verified,

                "operation":
                operation,

                "device":
                device.get(
                    "device_name"
                ),

                "push_success":
                True,

                "state_verified":
                verified,

                "message":
                (
                    "Configuration verified"
                    if verified
                    else
                    "Verification failed"
                ),

                "expected_state":
                self._build_expected_state(
                    operation,
                    payload
                ),

                "actual_state":
                device_facts,

                "evidence":
                evidence
            }

        except Exception as exc:

            logger.exception(

                "Verification failed"
            )

            return {

                "verified": False,

                "operation":
                operation,

                "device":
                device.get(
                    "device_name"
                ),

                "push_success":
                True,

                "state_verified":
                False,

                "message":
                str(exc),

                "expected_state":
                {},

                "actual_state":
                {},

                "evidence": {

                    "error":
                    str(exc)
                }
            }

    @staticmethod
    def _find_vlan(
        device_facts: Dict,
        vlan_id: int
    ):

        # Support both lookup formats:
        # - set (from _build_lookup_state): check membership
        # - list (raw): iterate
        vlans = device_facts.get("_raw_vlans") or device_facts.get("vlans", [])
        if isinstance(vlans, set):
            return {"vlan_id": vlan_id} if vlan_id in vlans else None

        return next(
            (v for v in vlans if v.get("vlan_id") == vlan_id),
            None
        )

    @staticmethod
    def _find_interface(
        device_facts: Dict,
        interface_name: str
    ):

        # Support both lookup formats:
        # - dict (from _build_lookup_state): direct key lookup
        # - list (raw): iterate
        interfaces = device_facts.get("interfaces", {})
        if isinstance(interfaces, dict):
            return interfaces.get(interface_name)

        return next(
            (i for i in interfaces if i.get("name") == interface_name),
            None
        )

    def _verify_vlan_creation(
        self,
        device_facts: Dict,
        payload: Dict
    ):
        """Verify VLAN creation matches expected state."""
        
        vlan_id = payload.get("vlan_id")
        expected_name = payload.get("vlan_name") or payload.get("name")
        
        if vlan_id is None:
            return False, {
                "error": f"Missing vlan_id in payload: {payload}"
            }
        
        vlan_id = int(vlan_id)
        vlan = self._find_vlan(device_facts, vlan_id)

        if not vlan:
            return False, {
                "error": f"VLAN {vlan_id} not found",
                "vlan_id": vlan_id
            }

        evidence = {
            "vlan_id": vlan_id,
            "verified": True
        }
        
        # Check VLAN name if specified and available in device facts
        if expected_name and isinstance(vlan, dict):
            actual_name = vlan.get("name")
            if actual_name and actual_name != expected_name:
                return False, {
                    "error": f"VLAN name is '{actual_name}', expected '{expected_name}'",
                    "vlan_id": vlan_id,
                    "expected_name": expected_name,
                    "actual_name": actual_name
                }
            if actual_name:
                evidence["vlan_name"] = actual_name

        return True, evidence

    def _verify_vlan_deletion(
        self,
        device_facts: Dict,
        payload: Dict
    ):
        """Verify VLAN deletion - VLAN should not exist."""
        
        vlan_id = payload.get("vlan_id")
        
        if vlan_id is None:
            return False, {
                "error": f"Missing vlan_id in payload: {payload}"
            }
        
        vlan_id = int(vlan_id)
        vlan = self._find_vlan(device_facts, vlan_id)

        if vlan is not None:
            return False, {
                "error": f"VLAN {vlan_id} still exists after deletion",
                "vlan_id": vlan_id
            }

        return True, {
            "vlan_id": vlan_id,
            "verified": True,
            "message": f"VLAN {vlan_id} successfully deleted"
        }

    def _verify_access_port(
        self,
        device_facts: Dict,
        payload: Dict
    ):
        """Verify access port configuration matches expected state."""
        
        interface_name = payload.get("interface")
        expected_vlan = payload.get("vlan_id") or payload.get("access_vlan")
        
        if not interface_name or expected_vlan is None:
            return False, {
                "error": f"Missing interface or vlan_id in payload: {payload}"
            }
        
        expected_vlan = int(expected_vlan)
        interface = self._find_interface(device_facts, interface_name)
        
        if not interface:
            return False, {
                "error": f"Interface {interface_name} not found",
                "interface": interface_name
            }
        
        # Check mode is access
        actual_mode = interface.get("mode", "").lower()
        if actual_mode != "access":
            return False, {
                "error": f"Interface mode is '{actual_mode}', expected 'access'",
                "interface": interface_name,
                "expected_mode": "access",
                "actual_mode": actual_mode
            }
        
        # Check access VLAN matches
        actual_vlan = interface.get("access_vlan")
        if actual_vlan != expected_vlan:
            return False, {
                "error": f"Access VLAN is {actual_vlan}, expected {expected_vlan}",
                "interface": interface_name,
                "expected_vlan": expected_vlan,
                "actual_vlan": actual_vlan
            }
        
        return True, {
            "interface": interface_name,
            "mode": "access",
            "access_vlan": expected_vlan,
            "verified": True
        }

    def _verify_trunk_port(
        self,
        device_facts: Dict,
        payload: Dict
    ):
        """Verify trunk port configuration matches expected state."""
        
        interface_name = payload.get("interface")
        expected_allowed_vlans = payload.get("allowed_vlans", [])
        expected_native_vlan = payload.get("native_vlan")
        
        if not interface_name:
            return False, {
                "error": f"Missing interface in payload: {payload}"
            }
        
        interface = self._find_interface(device_facts, interface_name)
        
        if not interface:
            return False, {
                "error": f"Interface {interface_name} not found",
                "interface": interface_name
            }
        
        # Check mode is trunk
        actual_mode = interface.get("mode", "").lower()
        if actual_mode != "trunk":
            return False, {
                "error": f"Interface mode is '{actual_mode}', expected 'trunk'",
                "interface": interface_name,
                "expected_mode": "trunk",
                "actual_mode": actual_mode
            }
        
        evidence = {
            "interface": interface_name,
            "mode": "trunk",
            "verified": True
        }
        
        # Check allowed VLANs if specified
        if expected_allowed_vlans:
            actual_allowed_vlans = interface.get("allowed_vlans", [])
            # Convert to sets for comparison (order doesn't matter)
            expected_set = set(int(v) for v in expected_allowed_vlans)
            actual_set = set(int(v) for v in actual_allowed_vlans) if actual_allowed_vlans else set()
            
            if expected_set != actual_set:
                return False, {
                    "error": f"Allowed VLANs mismatch",
                    "interface": interface_name,
                    "expected_allowed_vlans": sorted(expected_set),
                    "actual_allowed_vlans": sorted(actual_set)
                }
            
            evidence["allowed_vlans"] = sorted(expected_set)
        
        # Check native VLAN if specified
        if expected_native_vlan is not None:
            actual_native_vlan = interface.get("native_vlan")
            expected_native_vlan = int(expected_native_vlan)
            
            if actual_native_vlan != expected_native_vlan:
                return False, {
                    "error": f"Native VLAN is {actual_native_vlan}, expected {expected_native_vlan}",
                    "interface": interface_name,
                    "expected_native_vlan": expected_native_vlan,
                    "actual_native_vlan": actual_native_vlan
                }
            
            evidence["native_vlan"] = expected_native_vlan
        
        return True, evidence

    def _verify_interface_mode(
        self,
        device_facts: Dict,
        payload: Dict
    ):
        """Verify interface administrative state matches expected state."""

        interface_name = payload.get("interface")
        expected_state = (
            payload.get("administrative_state")
            or payload.get("state")
            or ""
        ).lower()

        if not interface_name or not expected_state:
            return False, {
                "error": f"Missing interface or administrative_state in payload: {payload}"
            }

        interface = self._find_interface(device_facts, interface_name)

        if not interface:
            return False, {
                "error": f"Interface {interface_name} not found",
                "interface": interface_name
            }

        # Device state uses "up"/"down" — normalize expected to same
        expected_normalized = "up" if expected_state == "up" else "down"
        actual_status = (interface.get("status") or "").lower()

        if actual_status != expected_normalized:
            return False, {
                "error": f"Interface status is '{actual_status}', expected '{expected_normalized}'",
                "interface": interface_name,
                "expected_status": expected_normalized,
                "actual_status": actual_status,
            }

        return True, {
            "interface": interface_name,
            "administrative_state": expected_normalized,
            "verified": True,
        }


    @staticmethod
    def _build_expected_state(

        operation,
        payload
    ):

        return {

            "operation":
            operation,

            **payload
        }