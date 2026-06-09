"""
Dependency Planner

Lightweight capability-based dependency resolution for workflow steps.

Responsibilities:
- Parse requires/provides from intent schemas
- Build dependency graph between workflow steps
- Topologically sort steps to derive execution order
- Detect circular dependencies
- Detect unsatisfied requirements

Does NOT:
- Simulate device state
- Duplicate network state logic
- Hardcode intent-specific behavior
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional

from app.registry.intent_registry import get_intent_schema, CANONICAL_INTENT_SCHEMAS


logger = logging.getLogger(__name__)


class DependencyPlanner:
    """
    Resolves workflow step dependencies using capability metadata.
    
    Each step declares:
    - requires: capabilities needed before execution
    - provides: capabilities produced after execution
    
    The planner builds a dependency graph and determines execution order.
    """

    def __init__(self):
        # Pattern to extract parameter references like {vlan_id}
        self._param_pattern = re.compile(r'\{(\w+)\}')

    def plan(
        self,
        workflow: List[Dict[str, Any]],
        current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze workflow and produce an execution plan.
        
        Args:
            workflow: List of workflow steps with intent_type and parameters
            current_state: Current device state from DeviceStateService
            
        Returns:
            {
                "valid": bool,
                "ordered_workflow": List[Dict],  # Steps in dependency order
                "dependency_graph": Dict,        # Step dependencies
                "provided_capabilities": Set,    # All capabilities that will be available
                "errors": List[Dict],            # Unsatisfied deps, cycles, etc.
                "reordered": bool,               # Whether order changed
            }
        """
        if not workflow:
            return {
                "valid": True,
                "ordered_workflow": [],
                "dependency_graph": {},
                "provided_capabilities": set(),
                "errors": [],
                "reordered": False,
            }

        # Step 1: Extract capabilities from current device state
        state_capabilities = self._extract_state_capabilities(current_state)

        # Step 2: Parse requires/provides for each step
        steps_meta = self._parse_workflow_capabilities(workflow)

        # Step 3: Build dependency graph
        graph, errors = self._build_dependency_graph(
            steps_meta,
            state_capabilities
        )

        if errors:
            return {
                "valid": False,
                "ordered_workflow": workflow,
                "dependency_graph": graph,
                "provided_capabilities": state_capabilities,
                "errors": errors,
                "reordered": False,
            }

        # Step 4: Topological sort to determine execution order
        sorted_indices, cycle_error = self._topological_sort(graph, len(workflow))

        if cycle_error:
            return {
                "valid": False,
                "ordered_workflow": workflow,
                "dependency_graph": graph,
                "provided_capabilities": state_capabilities,
                "errors": [cycle_error],
                "reordered": False,
            }

        # Step 5: Reorder workflow based on dependencies
        ordered_workflow = [workflow[i] for i in sorted_indices]
        reordered = sorted_indices != list(range(len(workflow)))

        # Step 6: Compute all capabilities that will be available after workflow
        all_capabilities = set(state_capabilities)
        for meta in steps_meta:
            all_capabilities.update(meta["provides"])

        return {
            "valid": True,
            "ordered_workflow": ordered_workflow,
            "dependency_graph": graph,
            "provided_capabilities": all_capabilities,
            "errors": [],
            "reordered": reordered,
            "original_to_new_order": sorted_indices,
        }

    def get_step_capabilities(
        self,
        intent_type: str,
        parameters: Dict[str, Any]
    ) -> Tuple[Set[str], Set[str]]:
        """
        Get resolved requires and provides for a single step.
        
        Returns:
            (requires_set, provides_set) with parameter values substituted
        """
        schema = get_intent_schema(intent_type)
        if not schema:
            return set(), set()

        requires = self._resolve_capabilities(
            schema.get("requires", []),
            parameters
        )
        provides = self._resolve_capabilities(
            schema.get("provides", []),
            parameters
        )

        return requires, provides

    def check_requirements_satisfied(
        self,
        step: Dict[str, Any],
        available_capabilities: Set[str],
        current_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Check if a step's requirements are satisfied.
        
        Requirements can be satisfied by:
        1. Current device state
        2. Capabilities provided by earlier workflow steps
        
        Args:
            step: Workflow step with intent_type and parameters
            available_capabilities: Capabilities from state + earlier steps
            current_state: Current device state for additional checks
            
        Returns:
            List of unsatisfied requirement errors (empty if all satisfied)
        """
        intent_type = step.get("intent_type")
        parameters = step.get("parameters", {})

        requires, _ = self.get_step_capabilities(intent_type, parameters)

        errors = []
        for req in requires:
            if not self._is_capability_satisfied(req, available_capabilities, current_state):
                errors.append({
                    "error_type": "unsatisfied_requirement",
                    "capability": req,
                    "intent_type": intent_type,
                    "message": f"Requirement '{req}' not satisfied by device state or workflow"
                })

        return errors

    def _extract_state_capabilities(
        self,
        current_state: Dict[str, Any]
    ) -> Set[str]:
        """
        Extract capability tokens from current device state.
        
        This translates device state into capability format without
        duplicating state logic - it just reads what DeviceStateService provides.
        """
        capabilities = set()

        # Extract VLAN capabilities
        vlans = current_state.get("vlans", {})
        if isinstance(vlans, set):
            for vlan_id in vlans:
                capabilities.add(f"vlan_exists:{vlan_id}")
        elif isinstance(vlans, dict):
            for vlan_id in vlans.keys():
                capabilities.add(f"vlan_exists:{vlan_id}")

        # Extract interface capabilities
        interfaces = current_state.get("interfaces", {})
        for iface_name, iface_data in interfaces.items():
            # Interface exists
            capabilities.add(f"interface_exists:{iface_name}")

            # Admin state
            admin_state = iface_data.get("admin_state", "").lower()
            status = iface_data.get("status", "").lower()
            
            # Interface is up if admin_state is "up" or status is not "down"
            if admin_state == "up" or (status != "down" and admin_state != "down"):
                capabilities.add(f"interface_up:{iface_name}")

            # Switchport mode
            mode = iface_data.get("mode", "").lower()
            if mode == "access":
                capabilities.add(f"interface_access_mode:{iface_name}")
                access_vlan = iface_data.get("access_vlan")
                if access_vlan:
                    capabilities.add(f"interface_vlan_assigned:{iface_name}:{access_vlan}")
            elif mode == "trunk":
                capabilities.add(f"interface_trunk_mode:{iface_name}")
            
            # Not routed (is switchport)
            if mode != "routed":
                capabilities.add(f"interface_switchport:{iface_name}")

        return capabilities

    def _parse_workflow_capabilities(
        self,
        workflow: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Parse requires/provides for each workflow step.
        """
        steps_meta = []

        for idx, step in enumerate(workflow):
            intent_type = step.get("intent_type")
            parameters = step.get("parameters", {})

            requires, provides = self.get_step_capabilities(intent_type, parameters)

            steps_meta.append({
                "index": idx,
                "intent_type": intent_type,
                "parameters": parameters,
                "requires": requires,
                "provides": provides,
            })

        return steps_meta

    def _resolve_capabilities(
        self,
        capability_patterns: List[str],
        parameters: Dict[str, Any]
    ) -> Set[str]:
        """
        Resolve capability patterns by substituting parameter values.
        
        Examples:
            "vlan_exists:{vlan_id}" with params {"vlan_id": 87}
            → "vlan_exists:87"
            
            "vlans_exist:{allowed_vlans}" with params {"allowed_vlans": [10, 20]}
            → {"vlan_exists:10", "vlan_exists:20"}
        """
        resolved = set()

        for pattern in capability_patterns:
            # Handle special case: vlans_exist expands to multiple vlan_exists
            if pattern.startswith("vlans_exist:"):
                param_match = self._param_pattern.search(pattern)
                if param_match:
                    param_name = param_match.group(1)
                    vlan_list = parameters.get(param_name, [])
                    if isinstance(vlan_list, list):
                        for vlan_id in vlan_list:
                            resolved.add(f"vlan_exists:{vlan_id}")
                continue

            # Standard parameter substitution
            result = pattern
            for match in self._param_pattern.finditer(pattern):
                param_name = match.group(1)
                param_value = parameters.get(param_name, "")
                result = result.replace(f"{{{param_name}}}", str(param_value))

            resolved.add(result)

        return resolved

    def _build_dependency_graph(
        self,
        steps_meta: List[Dict[str, Any]],
        state_capabilities: Set[str]
    ) -> Tuple[Dict[int, Set[int]], List[Dict[str, Any]]]:
        """
        Build a dependency graph between workflow steps.
        
        Returns:
            (graph, errors)
            - graph: {step_index: set of step indices this step depends on}
            - errors: list of unsatisfied requirement errors
        """
        graph: Dict[int, Set[int]] = defaultdict(set)
        errors = []

        # Map: capability → step index that provides it
        capability_providers: Dict[str, int] = {}

        # First pass: register all providers
        for meta in steps_meta:
            for cap in meta["provides"]:
                capability_providers[cap] = meta["index"]

        # Second pass: build dependencies
        for meta in steps_meta:
            step_idx = meta["index"]

            for req in meta["requires"]:
                # Check if satisfied by device state
                if self._capability_in_set(req, state_capabilities):
                    continue

                # Check if provided by another step
                provider_idx = self._find_provider(req, capability_providers)
                
                if provider_idx is not None:
                    if provider_idx != step_idx:
                        graph[step_idx].add(provider_idx)
                else:
                    # Requirement not satisfied by state or workflow
                    # Find candidate intents that could provide this capability
                    candidates = self._find_candidate_intents(req)
                    
                    errors.append({
                        "error_type": "unsatisfied_dependency",
                        "step": step_idx + 1,
                        "intent_type": meta["intent_type"],
                        "capability": req,
                        "message": (
                            f"Step {step_idx + 1} ({meta['intent_type']}) requires "
                            f"'{req}' which is not provided by device state or "
                            f"any workflow step"
                        ),
                        "candidate_intents": candidates
                    })

        return dict(graph), errors

    def _find_candidate_intents(
        self,
        capability: str
    ) -> List[Dict[str, Any]]:
        """
        Find intents that could provide a missing capability.
        
        Args:
            capability: The missing capability (e.g., "interface_up:GigabitEthernet1/0/1")
            
        Returns:
            List of candidate intents with suggested parameters:
            [
                {
                    "intent_type": "configure_interface_status",
                    "provides_pattern": "interface_up:{interface}",
                    "suggested_parameters": {
                        "interface": "GigabitEthernet1/0/1",
                        "administrative_state": "up"
                    }
                }
            ]
        """
        candidates = []
        
        # Parse the capability to extract type and value
        # e.g., "interface_up:GigabitEthernet1/0/1" → ("interface_up", "GigabitEthernet1/0/1")
        # e.g., "vlan_exists:87" → ("vlan_exists", "87")
        parts = capability.split(":", 1)
        cap_type = parts[0]
        cap_value = parts[1] if len(parts) > 1 else None
        
        # Search all intents for ones that provide this capability type
        for intent_name, schema in CANONICAL_INTENT_SCHEMAS.items():
            provides_patterns = schema.get("provides", [])
            
            for pattern in provides_patterns:
                # Check if this pattern matches the capability type
                pattern_type = pattern.split(":")[0]
                
                if pattern_type == cap_type:
                    # Found a matching intent - build suggested parameters
                    suggested_params = self._build_suggested_parameters(
                        intent_name,
                        schema,
                        pattern,
                        cap_type,
                        cap_value
                    )
                    
                    candidates.append({
                        "intent_type": intent_name,
                        "provides_pattern": pattern,
                        "suggested_parameters": suggested_params,
                        "description": schema.get("description", "")
                    })
                    break  # One match per intent is enough
        
        return candidates

    def _build_suggested_parameters(
        self,
        intent_name: str,
        schema: Dict[str, Any],
        provides_pattern: str,
        cap_type: str,
        cap_value: Optional[str]
    ) -> Dict[str, Any]:
        """
        Build suggested parameters for a candidate intent.
        
        Extracts parameter names from the provides pattern and maps
        the capability value to the appropriate parameter.
        """
        suggested = {}
        required_params = schema.get("required_parameters", [])
        param_types = schema.get("parameter_types", {})
        
        # Extract parameter references from the pattern
        # e.g., "interface_up:{interface}" → ["interface"]
        param_refs = self._param_pattern.findall(provides_pattern)
        
        # Map the capability value to the first parameter reference
        if cap_value and param_refs:
            param_name = param_refs[0]
            
            # Convert value to appropriate type
            param_type = param_types.get(param_name, str)
            try:
                if param_type == int:
                    suggested[param_name] = int(cap_value)
                else:
                    suggested[param_name] = cap_value
            except (ValueError, TypeError):
                suggested[param_name] = cap_value
        
        # Add default values for other required parameters based on capability type
        if cap_type == "interface_up" and intent_name == "configure_interface_status":
            suggested["administrative_state"] = "up"
        elif cap_type == "interface_down" and intent_name == "configure_interface_status":
            suggested["administrative_state"] = "down"
        elif cap_type == "vlan_exists" and intent_name == "create_vlan":
            # vlan_id should already be set from cap_value
            pass
        
        return suggested

    def _capability_in_set(
        self,
        capability: str,
        capability_set: Set[str]
    ) -> bool:
        """Check if a capability is in the set (exact match)."""
        return capability in capability_set

    def _find_provider(
        self,
        requirement: str,
        capability_providers: Dict[str, int]
    ) -> Optional[int]:
        """
        Find which step provides a required capability.
        
        Handles pattern matching for capabilities like interface_up
        where the provider might use interface_status.
        """
        # Direct match
        if requirement in capability_providers:
            return capability_providers[requirement]

        # Pattern-based matching for interface_up
        # configure_interface_status provides interface_up:{interface}
        # when administrative_state is "up"
        if requirement.startswith("interface_up:"):
            interface = requirement.split(":", 1)[1]
            # Check if any step provides interface_up for this interface
            for cap, idx in capability_providers.items():
                if cap == f"interface_up:{interface}":
                    return idx
                # Also check interface_status with "up" state
                if cap.startswith(f"interface_status:{interface}:"):
                    state = cap.split(":")[-1].lower()
                    if state == "up":
                        return idx

        return None

    def _topological_sort(
        self,
        graph: Dict[int, Set[int]],
        num_steps: int
    ) -> Tuple[List[int], Optional[Dict[str, Any]]]:
        """
        Topologically sort steps based on dependency graph.
        
        Uses Kahn's algorithm for cycle detection.
        
        Returns:
            (sorted_indices, cycle_error)
            - sorted_indices: steps in dependency order
            - cycle_error: error dict if cycle detected, None otherwise
        """
        # Build in-degree map
        in_degree = {i: 0 for i in range(num_steps)}
        adj_list: Dict[int, Set[int]] = defaultdict(set)

        for step_idx, deps in graph.items():
            for dep_idx in deps:
                adj_list[dep_idx].add(step_idx)
                in_degree[step_idx] += 1

        # Start with nodes that have no dependencies
        queue = [i for i in range(num_steps) if in_degree[i] == 0]
        sorted_indices = []

        while queue:
            # Sort queue to maintain stable ordering when possible
            queue.sort()
            node = queue.pop(0)
            sorted_indices.append(node)

            for neighbor in adj_list[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycle
        if len(sorted_indices) != num_steps:
            cycle_nodes = [i for i in range(num_steps) if in_degree[i] > 0]
            return [], {
                "error_type": "circular_dependency",
                "steps": [n + 1 for n in cycle_nodes],
                "message": (
                    f"Circular dependency detected involving steps: "
                    f"{[n + 1 for n in cycle_nodes]}"
                )
            }

        return sorted_indices, None

    def _is_capability_satisfied(
        self,
        capability: str,
        available_capabilities: Set[str],
        current_state: Dict[str, Any]
    ) -> bool:
        """
        Check if a capability is satisfied by available capabilities or state.
        """
        if capability in available_capabilities:
            return True

        # Additional state-based checks for edge cases
        # This delegates to the capability set which was built from state
        return False
