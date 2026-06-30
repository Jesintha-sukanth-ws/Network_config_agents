import logging

logger = logging.getLogger(__name__)


class StateValidator:

    def __init__(self):
        # Import here to avoid circular imports
        from app.workflow.dependency_planner import DependencyPlanner
        self._dependency_planner = DependencyPlanner()

    def validate_state(
        self,
        workflow: list,
        current_state: dict,
        provided_capabilities: set = None
    ) -> dict:
        """
        Validate workflow against device state and planned capabilities.
        
        Args:
            workflow: List of workflow steps
            current_state: Current device state from DeviceStateService
            provided_capabilities: Optional set of capabilities that will be
                                   provided by earlier workflow steps (from DependencyPlanner)
        """
        # If no provided_capabilities passed, extract from state only
        if provided_capabilities is None:
            provided_capabilities = self._dependency_planner._extract_state_capabilities(current_state)

        execution_plan = []
        errors = []
        required_changes = 0
        skipped_changes = 0

        vlans = current_state.get("vlans", {})
        interfaces = current_state.get("interfaces", {})

        # Build a name→vlan_id index from raw device state so VLAN name
        # uniqueness can be checked without hardcoding vendor constraints.
        # _raw_vlans is the authoritative list: [{"vlan_id": int, "name": str}, ...]
        raw_vlans = current_state.get("_raw_vlans", [])
        existing_vlan_names: dict = {
            v["name"].strip().lower(): v["vlan_id"]
            for v in raw_vlans
            if v.get("name", "").strip()
        }

        # Project future state as earlier steps in this workflow execute.
        # This prevents a configure_access_port from being skipped or
        # incorrectly evaluated because its prerequisite VLAN doesn't
        # exist yet in current_state — it will exist after step N runs.
        projected_vlans: set = set(vlans) if isinstance(vlans, set) else set(vlans)
        projected_vlan_names: dict = dict(existing_vlan_names)  # name→vlan_id
        projected_interfaces: dict = dict(interfaces)

        # Track capabilities provided by workflow steps as we iterate
        workflow_provided_capabilities: set = set(provided_capabilities)

        for step_index, step in enumerate(workflow, start=1):

            intent = step.get("intent_type")
            params = step.get("parameters", {})

            execute = True
            reason = None
            step_errors = []

            # Get this step's requirements and check against available capabilities
            step_requires, step_provides = self._dependency_planner.get_step_capabilities(
                intent, params
            )

            if intent == "create_vlan":
                vlan_id = params.get("vlan_id")
                requested_name = (params.get("name") or "").strip()

                if vlan_id in projected_vlans:
                    execute = False
                    reason = f"VLAN {vlan_id} already exists"
                else:
                    # Check VLAN name uniqueness against projected device state.
                    # Idempotency: same vlan_id + same name is handled above
                    # (vlan_id already in projected_vlans → skip).
                    # Here we only reach this branch when vlan_id is new.
                    if requested_name:
                        name_key = requested_name.lower()
                        conflicting_id = projected_vlan_names.get(name_key)
                        if conflicting_id is not None and conflicting_id != vlan_id:
                            step_errors.append({
                                "error_type": "duplicate_vlan_name",
                                "step": step_index,
                                "field": "name",
                                "message": (
                                    f"VLAN name '{requested_name}' is already used "
                                    f"by VLAN {conflicting_id}"
                                ),
                            })
                            execute = False
                            reason = (
                                f"VLAN name '{requested_name}' already in use "
                                f"by VLAN {conflicting_id}"
                            )

                    if execute:
                        # Project: this VLAN will exist after this step
                        projected_vlans.add(vlan_id)
                        if requested_name:
                            projected_vlan_names[requested_name.lower()] = vlan_id

            elif intent == "delete_vlan":
                vlan_id = params.get("vlan_id")
                if vlan_id not in projected_vlans:
                    execute = False
                    reason = f"VLAN {vlan_id} does not exist"
                else:
                    projected_vlans.discard(vlan_id)
                    # Remove the name projection for the deleted VLAN
                    projected_vlan_names = {
                        n: vid
                        for n, vid in projected_vlan_names.items()
                        if vid != vlan_id
                    }

            elif intent == "configure_access_port":
                interface = params.get("interface")
                vlan_id = params.get("vlan_id")
                current = projected_interfaces.get(interface, {})

                # NOTE: If VLAN doesn't exist, we DON'T fail pre-flight validation.
                # The dependency planner will automatically infer that create_vlan
                # needs to be executed first. This is more permissive than hardcoding
                # a validation error, which would block valid workflows where the
                # VLAN was requested in user intent but not yet generated by LLM.
                if vlan_id is not None and vlan_id not in projected_vlans:
                    # Log a warning but don't fail — dependency planner will handle it
                    logger.warning(
                        "VLAN %d referenced by %s but not yet created; "
                        "dependency planner will inject create_vlan step",
                        vlan_id, interface
                    )
                    # Project that this VLAN will exist after execution
                    # (assuming dependency planner will infer create_vlan)
                    projected_vlans.add(vlan_id)
                elif current.get("mode") == "routed":
                    # Interface is a Layer 3 routed port — cannot assign a VLAN.
                    # The operator must convert it to a switchport first.
                    step_errors.append({
                        "error_type": "interface_routed",
                        "step": step_index,
                        "field": "interface",
                        "message": (
                            f"Interface {interface} is a routed (Layer 3) port. "
                            f"It must be converted to a switchport before assigning a VLAN."
                        ),
                    })
                    execute = False
                    reason = f"{interface} is a routed port"
                elif (
                    current.get("mode") == "access"
                    and current.get("access_vlan") == vlan_id
                ):
                    execute = False
                    reason = f"{interface} already configured"
                
                if execute:
                    projected_interfaces[interface] = {
                        **current,
                        "mode": "access",
                        "access_vlan": vlan_id,
                    }

            elif intent == "configure_trunk_port":
                interface = params.get("interface")
                requested_vlans = sorted(params.get("allowed_vlans", []))
                native_vlan = params.get("native_vlan")
                current = projected_interfaces.get(interface, {})
                current_allowed = sorted(current.get("allowed_vlans", []))
                current_native = current.get("native_vlan")

                # NOTE: Similar to configure_access_port, if allowed VLANs don't exist,
                # don't fail. The dependency planner will infer that create_vlan steps
                # need to be added for missing VLANs.
                missing_vlans = [
                    vid for vid in requested_vlans
                    if vid not in projected_vlans
                ]
                if missing_vlans:
                    logger.warning(
                        "VLANs %s referenced by %s but not yet created; "
                        "dependency planner will inject create_vlan steps",
                        missing_vlans, interface
                    )
                    # Project these VLANs will exist (dependency planner will infer create_vlan)
                    projected_vlans.update(missing_vlans)
                elif (
                    current.get("mode") == "trunk"
                    and current_allowed == requested_vlans
                    and current_native == native_vlan
                ):
                    execute = False
                    reason = f"{interface} already configured"
                
                if execute:
                    projected_interfaces[interface] = {
                        **current,
                        "mode": "trunk",
                        "allowed_vlans": requested_vlans,
                        "native_vlan": native_vlan,
                    }

            elif intent == "configure_interface_status":
                interface = params.get("interface")
                requested = (params.get("administrative_state") or "").lower()
                current = projected_interfaces.get(interface, {}).get("admin_state")

                if current == requested:
                    execute = False
                    reason = f"{interface} already {requested}"
                else:
                    projected_interfaces.setdefault(interface, {})["admin_state"] = requested
                    # Update status for dependency tracking
                    if requested == "up":
                        projected_interfaces[interface]["status"] = "up"

            errors.extend(step_errors)

            # Add capabilities provided by this step to workflow capabilities
            if execute:
                workflow_provided_capabilities.update(step_provides)
                required_changes += 1
            else:
                skipped_changes += 1

            execution_plan.append({
                "step": step_index,
                "intent_type": intent,
                "parameters": params,
                "execute": execute,
                "reason": reason,
            })

        # If any step produced a hard error (not just a skip), mark unsafe
        # so the orchestrator rejects the workflow before execution.
        hard_error_types = {"duplicate_vlan_name", "interface_routed"}
        has_hard_errors = any(
            e.get("error_type") in hard_error_types for e in errors
        )

        return {
            "safe": not has_hard_errors,
            "errors": errors,
            "execution_plan": execution_plan,
            "summary": {
                "required_changes": required_changes,
                "skipped_changes": skipped_changes,
            },
        }