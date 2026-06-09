"""
Display Service - Terminal output presentation layer.

Consumes the orchestrator's final result shape:

    {
        "task_number":  str,
        "device":       dict,
        "policy":       dict,
        "device_state": dict,   # current_state from DeviceStateService
        "results":      list[dict],
        "status":       str  # success | partial_failure | error | rejected
    }
"""

import json
import logging

logger = logging.getLogger(__name__)


def display_terminal_output(result: dict) -> None:

    if not isinstance(result, dict):
        logger.info("%s", result)
        return

    if result.get("status") == "error":
        _display_error_result(result)
        return

    _display_orchestration_result(result)


# ---------------------------------------------------------------
# Orchestration result
# ---------------------------------------------------------------

def _display_orchestration_result(result: dict) -> None:

    output = []

    output.append("\n" + "=" * 120)
    output.append("ORCHESTRATION RESULT")
    output.append("=" * 120)

    # ── Task summary ────────────────────────────────────────────
    task_number = result.get("task_number", "N/A")
    overall_status = result.get("status", "unknown")

    output.append("\nTASK INFORMATION")
    output.append("-" * 120)
    output.append(f"Task Number    : {task_number}")
    output.append(f"Overall Status : {overall_status}")

    # ── Device ──────────────────────────────────────────────────
    device = result.get("device") or {}
    if device:
        output.append("\nDEVICE INFORMATION")
        output.append("-" * 120)
        output.append(f"Device Name     : {device.get('device_name', 'N/A')}")
        output.append(f"Vendor          : {device.get('vendor', 'N/A')}")
        output.append(f"Model           : {device.get('model', 'N/A')}")
        output.append(f"OS Type         : {device.get('os_type', 'N/A')}")
        output.append(f"Management Host : {device.get('management_host', 'N/A')}")

    # ── Policy summary ──────────────────────────────────────────
    policy = result.get("policy") or {}
    if policy:
        output.append("\nRESOLVED POLICY")
        output.append("-" * 120)
        output.append(f"Vendor          : {policy.get('vendor', 'N/A')}")
        output.append(f"OS              : {policy.get('os', 'N/A')}")
        output.append(f"Model Family    : {policy.get('model_family', 'N/A')}")
        output.append(f"Schema Version  : {policy.get('schema_version', 'N/A')}")

        vlan_rules = policy.get("vlan_rules", {})
        vlan_range = vlan_rules.get("vlan_range")
        if vlan_range:
            output.append(f"VLAN Range      : {vlan_range[0]}-{vlan_range[1]}")

        policy_reserved = set(vlan_rules.get("reserved_vlans", []))
        if policy_reserved:
            output.append(
                f"Reserved VLANs  : {', '.join(str(v) for v in sorted(policy_reserved))}"
            )

    # ── Device state: VLANs ─────────────────────────────────────
    device_state = result.get("device_state") or {}
    raw_vlans = device_state.get("_raw_vlans") or []
    raw_interfaces = device_state.get("_raw_interfaces") or []

    if raw_vlans:
        policy_reserved = set(
            (policy.get("vlan_rules") or {}).get("reserved_vlans", [])
        )

        # Classify VLANs using the device's own data as ground truth.
        # A VLAN is treated as a system VLAN if the device itself reports it
        # with a well-known system name (case-insensitive prefix match).
        # This reflects what is actually on the device, not a hardcoded list.
        _SYSTEM_NAME_PREFIXES = (
            "default",
            "fddi",
            "token-ring",
            "fddinet",
            "trnet",
        )

        def _is_system_vlan(vlan_id: int, name: str) -> bool:
            if vlan_id == 1:
                return True
            name_lower = (name or "").strip().lower()
            return any(name_lower.startswith(p) for p in _SYSTEM_NAME_PREFIXES)

        system_vlans   = []
        reserved_vlans = []
        user_vlans     = []

        for v in sorted(raw_vlans, key=lambda x: x.get("vlan_id", 0)):
            vid  = v.get("vlan_id")
            name = v.get("name", "") or ""

            if _is_system_vlan(vid, name):
                system_vlans.append((vid, name))
            elif vid in policy_reserved:
                reserved_vlans.append((vid, name))
            else:
                user_vlans.append((vid, name))

        output.append("\nDEVICE VLAN TABLE")
        output.append("-" * 120)

        if system_vlans:
            output.append("  System VLANs (reported by device):")
            for vid, name in system_vlans:
                label = f"    VLAN {vid:<6}"
                if name:
                    label += f"  {name}"
                output.append(label)

        if reserved_vlans:
            output.append("  Policy-Reserved VLANs (present on device):")
            for vid, name in reserved_vlans:
                label = f"    VLAN {vid:<6}"
                if name:
                    label += f"  {name}"
                output.append(label)

        # Show policy-reserved VLANs that are NOT yet on the device
        device_vlan_ids = {v.get("vlan_id") for v in raw_vlans}
        absent_reserved = sorted(policy_reserved - device_vlan_ids)
        if absent_reserved:
            output.append("  Policy-Reserved VLANs (not present on device):")
            for vid in absent_reserved:
                output.append(f"    VLAN {vid:<6}  (absent)")

        if user_vlans:
            output.append("  User VLANs:")
            for vid, name in user_vlans:
                label = f"    VLAN {vid:<6}"
                if name:
                    label += f"  {name}"
                output.append(label)

    # ── Device state: Interfaces ─────────────────────────────────
    if raw_interfaces:
        output.append("\nDEVICE INTERFACE TABLE")
        output.append("-" * 120)
        headers = ("Interface", "Mode", "Access VLAN", "Allowed VLANs", "Native VLAN", "Status")
        widths   = (32, 8, 13, 30, 13, 8)
        output.append(_format_row(headers, widths))
        output.append("-" * 120)

        for intf in sorted(raw_interfaces, key=lambda x: x.get("name", "")):
            name        = intf.get("name", "-")
            mode        = intf.get("mode", "-")
            access_vlan = str(intf.get("access_vlan", "-"))
            allowed     = str(intf.get("allowed_vlans", "-"))
            native      = str(intf.get("native_vlan", "-"))
            status      = intf.get("status", "-")

            output.append(_format_row(
                (name, mode, access_vlan, allowed, native, status),
                widths,
            ))

    # ── Step results ─────────────────────────────────────────────
    results = result.get("results") or []
    if results:
        output.append("\nSTEP RESULTS")
        output.append("-" * 120)
        headers = ("Step", "Operation", "Status", "Detail")
        widths  = (6, 30, 12, 60)
        output.append(_format_row(headers, widths))
        output.append("-" * 120)

        for entry in results:
            step      = str(entry.get("step", "-"))
            operation = str(entry.get("operation", "-"))
            status    = str(entry.get("status", "-")).upper()
            detail    = (
                entry.get("reason")
                or entry.get("error")
                or entry.get("verify", {}).get("message")
                or entry.get("push", {}).get("message")
                or ""
            )
            output.append(_format_row(
                (step, operation, status, str(detail)),
                widths,
            ))

    # ── Per-step VLAN/interface context ──────────────────────────
    # For access_port and trunk_port steps, show what was assigned.
    for entry in results:
        operation = entry.get("operation", "")
        params    = entry.get("parameters") or {}
        verify    = entry.get("verify") or {}
        push      = entry.get("push") or {}

        if operation in ("configure_access_port", "access_port"):
            interface = params.get("interface", "-")
            vlan_id   = params.get("vlan_id", "-")
            vlan_name = _lookup_vlan_name(vlan_id, raw_vlans)
            output.append("")
            output.append(f"  Step {entry.get('step')} [access_port assignment]")
            output.append(f"    Interface  : {interface}")
            output.append(f"    VLAN ID    : {vlan_id}")
            if vlan_name:
                output.append(f"    VLAN Name  : {vlan_name}")
            output.append(f"    Status     : {entry.get('status', '-').upper()}")

        elif operation in ("configure_trunk_port", "trunk_port"):
            interface    = params.get("interface", "-")
            allowed      = params.get("allowed_vlans", [])
            native       = params.get("native_vlan", "-")
            output.append("")
            output.append(f"  Step {entry.get('step')} [trunk_port assignment]")
            output.append(f"    Interface    : {interface}")
            output.append(f"    Allowed VLANs: {', '.join(str(v) for v in allowed)}")
            output.append(f"    Native VLAN  : {native}")
            output.append(f"    Status       : {entry.get('status', '-').upper()}")

        elif operation in ("create_vlan", "delete_vlan"):
            vlan_id   = params.get("vlan_id", "-")
            vlan_name = params.get("name") or params.get("vlan_name") or ""
            output.append("")
            output.append(f"  Step {entry.get('step')} [{operation}]")
            output.append(f"    VLAN ID    : {vlan_id}")
            if vlan_name:
                output.append(f"    VLAN Name  : {vlan_name}")
            output.append(f"    Status     : {entry.get('status', '-').upper()}")

        # Always dump push/verify JSON for non-skipped steps
        if push or verify:
            if push:
                output.append("    PUSH:")
                output.append(_indent_json(push, indent=6))
            if verify:
                output.append("    VERIFY:")
                output.append(_indent_json(verify, indent=6))

    output.append("\n" + "=" * 120)
    output.append(f"ORCHESTRATION {overall_status.upper()}")
    output.append("=" * 120 + "\n")

    logger.info("\n%s", "\n".join(output))


def _display_error_result(result: dict) -> None:

    output = []
    output.append("\n" + "=" * 120)
    output.append("ORCHESTRATION ERROR")
    output.append("=" * 120)

    output.append(f"\nTask Number : {result.get('task_number', 'N/A')}")
    output.append(f"Status      : {result.get('status', 'error')}")
    output.append(f"\nMessage:\n  {result.get('message', 'No details available')}")

    output.append("\n" + "=" * 120 + "\n")
    logger.info("\n%s", "\n".join(output))


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _lookup_vlan_name(vlan_id, raw_vlans: list) -> str:
    """Return the name of a VLAN from the raw device VLAN list, or ''."""
    for v in raw_vlans:
        if v.get("vlan_id") == vlan_id:
            return v.get("name", "") or ""
    return ""


def _format_row(values, widths) -> str:
    """
    Format a row with at least one space between every column,
    even when a value exceeds its allotted width.
    """
    parts = []
    for value, width in zip(values, widths):
        text = str(value)
        if len(text) >= width:
            parts.append(text + " ")
        else:
            parts.append(text.ljust(width))
    return "".join(parts).rstrip()


def _indent_json(payload: dict, indent: int = 4) -> str:
    raw = json.dumps(payload, indent=2, default=str)
    pad = " " * indent
    return "\n".join(pad + line for line in raw.splitlines())
