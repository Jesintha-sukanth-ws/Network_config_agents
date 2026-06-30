"""
Service for computing efficient device state diffs.

Instead of showing full device state (1000+ fields), compute the diff between
before and after states and show only changed fields with before→after values.
"""

import json
import logging
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class StateDiffService:
    """Compute and format state diffs for efficient UI display."""

    # Critical fields that warrant highlighting in UI
    CRITICAL_FIELDS = {
        "interfaces",
        "vlan",
        "vlans",
        "ip_address",
        "ipv4_address",
        "ipv6_address",
        "gateway",
        "default_gateway",
        "ip",
        "subnet",
        "netmask",
        "prefix",
        "route",
        "routing",
    }

    # Max changes to display (prevent overwhelming UI)
    MAX_DISPLAY_CHANGES = 50

    @staticmethod
    def _is_critical_field(field_name: str) -> bool:
        """Check if a field is critical (interfaces, VLANs, IPs, etc.)."""
        field_lower = field_name.lower()
        for critical in StateDiffService.CRITICAL_FIELDS:
            if critical in field_lower:
                return True
        return False

    @staticmethod
    def _deep_dict_diff(before: Dict, after: Dict, path: str = "") -> List[Dict[str, Any]]:
        """
        Recursively diff two dicts, returning list of changed fields.
        
        Returns:
            List of dicts with keys:
            - field: Full path to field (e.g., "interfaces.GigabitEthernet1/0/1.vlan")
            - before: Old value (truncated if long)
            - after: New value (truncated if long)
            - critical: True if field is critical
        """
        changes = []

        # Check for keys in before
        for key in before.keys():
            full_path = f"{path}.{key}" if path else key
            
            if key not in after:
                # Key was removed
                changes.append({
                    "field": full_path,
                    "before": StateDiffService._truncate_value(before[key]),
                    "after": None,
                    "type": "removed",
                    "critical": StateDiffService._is_critical_field(key),
                })
            elif isinstance(before[key], dict) and isinstance(after[key], dict):
                # Recurse into nested dicts
                changes.extend(
                    StateDiffService._deep_dict_diff(before[key], after[key], full_path)
                )
            elif before[key] != after[key]:
                # Value changed
                changes.append({
                    "field": full_path,
                    "before": StateDiffService._truncate_value(before[key]),
                    "after": StateDiffService._truncate_value(after[key]),
                    "type": "modified",
                    "critical": StateDiffService._is_critical_field(key),
                })

        # Check for new keys in after
        for key in after.keys():
            if key not in before:
                full_path = f"{path}.{key}" if path else key
                changes.append({
                    "field": full_path,
                    "before": None,
                    "after": StateDiffService._truncate_value(after[key]),
                    "type": "added",
                    "critical": StateDiffService._is_critical_field(key),
                })

        return changes

    @staticmethod
    def _truncate_value(value: Any, max_length: int = 100) -> str:
        """Convert value to string, truncating if too long."""
        if value is None:
            return None
        
        if isinstance(value, dict):
            value_str = json.dumps(value, indent=2, default=str)
        elif isinstance(value, list):
            value_str = json.dumps(value, indent=2, default=str)
        else:
            value_str = str(value)

        if len(value_str) > max_length:
            return value_str[:max_length] + "..."
        
        return value_str

    @staticmethod
    def compute_diff(before_state: Dict[str, Any], after_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute efficient state diff.
        
        Args:
            before_state: Device state before changes
            after_state: Device state after changes
        
        Returns:
            Dict with:
            - total_changes: Total number of changes
            - added: Count of added fields
            - modified: Count of modified fields
            - removed: Count of removed fields
            - changes: List of change objects (limited to MAX_DISPLAY_CHANGES)
            - truncated: True if >MAX_DISPLAY_CHANGES changes exist
        """
        try:
            # Compute all changes
            all_changes = StateDiffService._deep_dict_diff(before_state, after_state)

            # Count by type
            added = sum(1 for c in all_changes if c["type"] == "added")
            modified = sum(1 for c in all_changes if c["type"] == "modified")
            removed = sum(1 for c in all_changes if c["type"] == "removed")

            # Sort: critical first, then by type (removed, modified, added)
            all_changes.sort(
                key=lambda x: (
                    not x["critical"],  # Critical first
                    {"removed": 0, "modified": 1, "added": 2}[x["type"]],
                    x["field"],
                )
            )

            # Truncate if too many
            truncated = len(all_changes) > StateDiffService.MAX_DISPLAY_CHANGES
            display_changes = all_changes[: StateDiffService.MAX_DISPLAY_CHANGES]

            return {
                "total_changes": len(all_changes),
                "added": added,
                "modified": modified,
                "removed": removed,
                "changes": display_changes,
                "truncated": truncated,
            }

        except Exception as e:
            logger.error("Error computing state diff: %s", e)
            return {
                "total_changes": 0,
                "added": 0,
                "modified": 0,
                "removed": 0,
                "changes": [],
                "truncated": False,
                "error": str(e),
            }

    @staticmethod
    def get_summary(diff: Dict[str, Any]) -> str:
        """Get human-readable summary of diff."""
        total = diff.get("total_changes", 0)
        added = diff.get("added", 0)
        modified = diff.get("modified", 0)
        removed = diff.get("removed", 0)
        truncated = diff.get("truncated", False)

        summary = f"{total} total changes ({added} added, {modified} modified, {removed} removed)"
        if truncated:
            summary += f" - showing first {StateDiffService.MAX_DISPLAY_CHANGES}"

        return summary
