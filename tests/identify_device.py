"""
identify_device.py

Standalone helper that asks a Cisco device to identify itself, then
prints exactly what to put in each ServiceNow CMDB field.

Reads host/credentials from environment (.env) by default. CLI args
override.

Usage:
    venv\\Scripts\\python.exe tests\\identify_device.py
    venv\\Scripts\\python.exe tests\\identify_device.py --host devnetsandboxiosxec9k.cisco.com
    venv\\Scripts\\python.exe tests\\identify_device.py --host 10.0.0.1 -u admin -p secret

What it queries (RESTCONF first; falls back to NX-API if REST fails):
    - Cisco-IOS-XE-native:native/version
    - Cisco-IOS-XE-native:native/hostname
    - Cisco-IOS-XE-device-hardware-oper:device-hardware-data
    - openconfig-platform:components       (any vendor that supports it)
    - NX-API: show version | json          (Nexus / NX-OS)

Output is a "CMDB FIELDS" block that maps observed values 1:1 onto
the fields cmdb_service.py reads:

    name             -> cmdb_ci_comm.name
    manufacturer     -> cmdb_ci_comm.manufacturer  (vendor)
    u_os_type        -> cmdb_ci_comm.u_os_type
    model_number     -> cmdb_ci_comm.model_number
    fqdn             -> cmdb_ci_comm.fqdn
    ip_address       -> cmdb_ci_comm.ip_address
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import urllib3


# -------------------------------------------------------------------
# Bootstrap so the script runs from the project root without install
# -------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env so CISCO_USERNAME / CISCO_PASSWORD are picked up
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(_PROJECT_ROOT / ".env")
except Exception:
    pass


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# -------------------------------------------------------------------
# Pretty printers
# -------------------------------------------------------------------

def banner(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def section(title: str) -> None:
    print()
    print("-" * 80)
    print(title)
    print("-" * 80)


def kv(label: str, value: Any) -> None:
    print(f"  {label:<22} {value}")


def first(*values) -> str:
    """Return the first non-empty string-coerced value, else ''."""
    for v in values:
        if v is None:
            continue
        text = str(v).strip()
        if text:
            return text
    return ""


# -------------------------------------------------------------------
# RESTCONF helpers
# -------------------------------------------------------------------

def rc_get(
    host: str,
    port: int,
    path: str,
    auth: Tuple[str, str],
    timeout: int,
) -> Optional[Dict[str, Any]]:
    """GET a RESTCONF data path. Returns parsed JSON, or None on any failure."""
    url = f"https://{host}:{port}/restconf/data/{path.lstrip('/')}"
    try:
        r = requests.get(
            url,
            auth=auth,
            headers={"Accept": "application/yang-data+json"},
            verify=False,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        print(f"    [skip] {path}: {exc}")
        return None

    if r.status_code == 404:
        return None
    if r.status_code >= 400:
        print(f"    [skip] {path}: HTTP {r.status_code}")
        return None
    try:
        return r.json()
    except ValueError:
        return None


def collect_iosxe(
    host: str,
    port: int,
    auth: Tuple[str, str],
    timeout: int,
) -> Dict[str, Any]:
    """Pull every IOS-XE / OpenConfig oper path that holds device identity."""

    paths = {
        "version_native":
            "Cisco-IOS-XE-native:native/version",
        "hostname_native":
            "Cisco-IOS-XE-native:native/hostname",
        "device_hw_oper":
            "Cisco-IOS-XE-device-hardware-oper:device-hardware-data",
        "platform_oper":
            "Cisco-IOS-XE-platform-oper:components",
        "openconfig_platform":
            "openconfig-platform:components",
    }

    facts: Dict[str, Any] = {}
    for label, path in paths.items():
        data = rc_get(host, port, path, auth, timeout)
        if data is not None:
            facts[label] = data

    return facts


# -------------------------------------------------------------------
# NX-API fallback
# -------------------------------------------------------------------

def collect_nxapi_show_version(
    host: str,
    port: int,
    auth: Tuple[str, str],
    timeout: int,
) -> Optional[Dict[str, Any]]:
    """Try `show version | json` over NX-API (Nexus)."""

    url = f"https://{host}:{port}/ins"
    payload = {
        "ins_api": {
            "version": "1.0",
            "type": "cli_show",
            "chunk": "0",
            "sid": "1",
            "input": "show version",
            "output_format": "json",
        }
    }
    try:
        r = requests.post(
            url,
            auth=auth,
            json=payload,
            headers={"Content-Type": "application/json"},
            verify=False,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        print(f"    [skip] NX-API show version: {exc}")
        return None

    if r.status_code >= 400:
        print(f"    [skip] NX-API show version: HTTP {r.status_code}")
        return None
    try:
        return r.json()
    except ValueError:
        return None


# -------------------------------------------------------------------
# Field extractors — all defensive, no hardcoded model/vendor strings
# -------------------------------------------------------------------

def extract_iosxe_identity(facts: Dict[str, Any]) -> Dict[str, str]:
    """Pull hostname / OS / version / chassis model from IOS-XE oper data."""

    out = {
        "hostname": "",
        "os_type": "",
        "os_version": "",
        "model_number": "",
        "vendor": "",
        "serial": "",
    }

    # Hostname
    hostname_native = facts.get("hostname_native", {})
    out["hostname"] = first(
        hostname_native.get("Cisco-IOS-XE-native:hostname")
    )

    # Software version (and confirms IOS-XE-ness)
    version_native = facts.get("version_native", {})
    out["os_version"] = first(
        version_native.get("Cisco-IOS-XE-native:version")
    )
    if out["os_version"]:
        out["os_type"] = "IOS-XE"
        out["vendor"] = "Cisco"

    # Chassis model — try device-hardware-oper first (most reliable)
    hw = (
        facts
        .get("device_hw_oper", {})
        .get("Cisco-IOS-XE-device-hardware-oper:device-hardware-data", {})
        .get("device-hardware", {})
    )
    inventory: List[Dict[str, Any]] = hw.get(
        "device-inventory", []
    ) or []
    for item in inventory:
        # 'hw-type' tags the role of the entry — chassis is what we want
        if "chassis" in str(item.get("hw-type", "")).lower():
            out["model_number"] = first(
                item.get("part-number"),
                item.get("hw-pid"),
                item.get("model-name"),
                out["model_number"],
            )
            out["serial"] = first(
                item.get("serial-number"),
                out["serial"],
            )
            break

    # Fallback — OpenConfig components (works on many Cisco devices too)
    if not out["model_number"]:
        oc = (
            facts
            .get("openconfig_platform", {})
            .get("openconfig-platform:components", {})
            .get("component", [])
        )
        for component in oc or []:
            state = component.get("state", {})
            if str(state.get("type", "")).lower().endswith("chassis"):
                out["model_number"] = first(
                    state.get("part-no"),
                    state.get("hardware-version"),
                    out["model_number"],
                )
                out["serial"] = first(
                    state.get("serial-no"),
                    out["serial"],
                )
                break

    return out


def extract_nxos_identity(show_version_json: Dict[str, Any]) -> Dict[str, str]:
    """Pull identity fields from NX-API `show version` JSON."""

    out = {
        "hostname": "",
        "os_type": "",
        "os_version": "",
        "model_number": "",
        "vendor": "",
        "serial": "",
    }

    body = (
        show_version_json
        .get("ins_api", {})
        .get("outputs", {})
        .get("output", {})
        .get("body", {})
    )
    if not body:
        return out

    # NX-API key names are stable per platform; fields are read defensively
    out["hostname"] = first(body.get("host_name"))
    out["os_version"] = first(
        body.get("nxos_ver_str"),
        body.get("kickstart_ver_str"),
        body.get("rr_sys_ver"),
    )
    out["model_number"] = first(body.get("chassis_id"))
    out["serial"] = first(body.get("proc_board_id"))
    if out["os_version"]:
        out["os_type"] = "NX-OS"
        out["vendor"] = "Cisco"

    return out


# -------------------------------------------------------------------
# Suggestion logic — recommend a model_family value the policy
# resolver will accept, without hardcoding any model name.
# -------------------------------------------------------------------

def suggest_model_family(model_number: str) -> str:
    """
    Heuristic that mirrors how Cisco names families: the longest
    leading run of letters is treated as the family hint, optionally
    followed by '9000'-style series tokens. Examples:
        C9300-48P    -> C9300
        N9K-C93180YC -> N9K
        ASR1006      -> ASR1006
    The result is presented as a *suggestion*; whatever the operator
    stores in CMDB just needs to match what the corresponding
    policy.json declares in its 'model_family' field.
    """
    if not model_number:
        return ""
    head = ""
    for ch in model_number:
        if ch.isalnum():
            head += ch
            # Stop at the first hyphen-equivalent break
        else:
            break
    return head


def cmdb_field_block(identity: Dict[str, str], host_arg: str) -> None:
    """Print the explicit CMDB-field instructions."""

    section("CMDB FIELDS — copy these into the ServiceNow CI")

    print(
        "  Path: ServiceNow → Configuration → CI Class Manager →"
        " Communication Device (cmdb_ci_comm)\n"
    )

    kv("name",           identity.get("hostname") or "<set to the device hostname>")
    kv("manufacturer",   identity.get("vendor") or "<unknown>")
    kv("u_os_type",      identity.get("os_type") or "<unknown>")
    kv("model_number",   identity.get("model_number") or "<unknown>")

    # FQDN vs IP — preserve whatever was used to reach the device
    if "." in host_arg and not host_arg.replace(".", "").isdigit():
        kv("fqdn",       host_arg)
        kv("ip_address", "<leave blank or set to the resolved IP>")
    else:
        kv("fqdn",       "<optional>")
        kv("ip_address", host_arg)

    suggested_family = suggest_model_family(identity.get("model_number", ""))
    if suggested_family:
        section("POLICY FILE HINT")
        kv("suggested model_family", suggested_family)
        print(
            "\n  Make sure data/policies/<file>.json declares the SAME\n"
            "  model_family for an exact match. If you prefer broader\n"
            "  matching, leave model_family empty in the JSON and the\n"
            "  resolver will fall back to vendor+os."
        )


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Identify a Cisco device for CMDB onboarding."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("DEVICE_HOST", ""),
        help="Device FQDN or IP. Defaults to $DEVICE_HOST or the first .env hint.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("DEVICE_PORT", "443")),
        help="Management port (default 443).",
    )
    parser.add_argument(
        "-u", "--username",
        default=os.getenv("CISCO_USERNAME", ""),
        help="Username (default $CISCO_USERNAME from .env).",
    )
    parser.add_argument(
        "-p", "--password",
        default=os.getenv("CISCO_PASSWORD", ""),
        help="Password (default $CISCO_PASSWORD from .env).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("DEVICE_TIMEOUT", "20")),
        help="Per-request timeout in seconds (default 20).",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Also print the raw JSON returned by every probe.",
    )

    args = parser.parse_args()

    # Sensible default if nothing was set: the host already used in .env
    if not args.host:
        # Last resort — the host that's been hitting the live runs
        args.host = "devnetsandboxiosxec9k.cisco.com"

    if not args.username or not args.password:
        print(
            "ERROR: missing credentials. Set CISCO_USERNAME / CISCO_PASSWORD\n"
            "       in .env, or pass -u / -p on the command line."
        )
        return 2

    auth = (args.username, args.password)

    banner(f"DEVICE IDENTIFICATION  ({args.host}:{args.port})")

    # ---- IOS-XE / OpenConfig probes ----
    section("Probing RESTCONF (IOS-XE / OpenConfig)")
    iosxe_facts = collect_iosxe(args.host, args.port, auth, args.timeout)
    iosxe_identity = (
        extract_iosxe_identity(iosxe_facts) if iosxe_facts else {}
    )

    if iosxe_identity.get("os_version"):
        kv("hostname",     iosxe_identity.get("hostname") or "<not reported>")
        kv("vendor",       iosxe_identity.get("vendor"))
        kv("os_type",      iosxe_identity.get("os_type"))
        kv("os_version",   iosxe_identity.get("os_version"))
        kv("model_number", iosxe_identity.get("model_number") or "<not reported>")
        kv("serial",       iosxe_identity.get("serial") or "<not reported>")
    else:
        print("  RESTCONF returned no IOS-XE identity data.")

    # ---- NX-OS fallback only if RESTCONF gave us nothing useful ----
    nxos_identity: Dict[str, str] = {}
    if not iosxe_identity.get("os_version"):
        section("Probing NX-API (NX-OS)")
        show_ver = collect_nxapi_show_version(
            args.host, args.port, auth, args.timeout
        )
        if show_ver:
            nxos_identity = extract_nxos_identity(show_ver)
            if nxos_identity.get("os_version"):
                kv("hostname",     nxos_identity.get("hostname") or "<not reported>")
                kv("vendor",       nxos_identity.get("vendor"))
                kv("os_type",      nxos_identity.get("os_type"))
                kv("os_version",   nxos_identity.get("os_version"))
                kv("model_number", nxos_identity.get("model_number") or "<not reported>")
                kv("serial",       nxos_identity.get("serial") or "<not reported>")
            else:
                print("  NX-API responded but identity could not be parsed.")
        else:
            print("  NX-API not reachable.")

    # ---- Pick whichever probe succeeded ----
    identity = (
        iosxe_identity
        if iosxe_identity.get("os_version")
        else nxos_identity
    )

    if not identity or not identity.get("os_type"):
        section("RESULT")
        print("  Could not identify the device automatically.")
        print("  Run again with --raw, or SSH in and use 'show version'.")
        return 1

    cmdb_field_block(identity, args.host)

    if args.raw:
        section("RAW IOS-XE PROBE OUTPUT")
        print(json.dumps(iosxe_facts, indent=2, default=str))

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
