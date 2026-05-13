"""
Display Service - Terminal output presentation layer
Responsible for formatting and printing orchestration results to terminal
"""


def display_terminal_output(result: dict):
    """
    Display orchestration result in terminal.
    Formats and prints the unified orchestration result.
    
    Args:
        result: Unified orchestration result from orchestrator
    """
    if "error" in result:
        _display_error_result(result)
    else:
        _display_success_result(result)


def _display_success_result(result: dict):
    """Display successful orchestration result"""
    
    output = []
    
    # Header
    output.append("\n" + "=" * 120)
    output.append("ORCHESTRATION RESULT")
    output.append("=" * 120)
    
    # Task Information
    task = result.get("task", {})
    output.append("\n📋 TASK INFORMATION")
    output.append("-" * 120)
    output.append(f"Task Number:    {task.get('task_number', 'N/A')}")
    output.append(f"Task ID:        {task.get('sys_id', 'N/A')}")
    output.append(f"Description:    {task.get('description', 'N/A')}")
    
    # Device Information
    device = result.get("device", {})
    output.append("\n🖥️  DEVICE INFORMATION")
    output.append("-" * 120)
    output.append(f"Device Name:    {device.get('device_name', 'N/A')}")
    output.append(f"Vendor:         {device.get('vendor', 'N/A')}")
    output.append(f"Model:          {device.get('model', 'N/A')}")
    output.append(f"OS Type:        {device.get('os_type', 'N/A')}")
    output.append(f"OS Version:     {device.get('os_version', 'N/A')}")
    output.append(f"Management IP:  {device.get('management_host', 'N/A')}")
    
    # Intent Workflow
    intent = result.get("intent", {})
    workflow = intent.get("workflow", [])
    
    output.append("\n🎯 INTENT WORKFLOW")
    output.append("-" * 120)
    
    if workflow:
        for idx, step in enumerate(workflow, 1):
            intent_type = step.get("intent_type", "unknown")
            parameters = step.get("parameters", {})
            
            output.append(f"\nStep {idx}: {intent_type.replace('_', ' ').title()}")
            
            for key, value in parameters.items():
                output.append(f"  • {key.replace('_', ' ').title()}: {value}")
    else:
        output.append("No workflow steps defined")
    
    # Device Facts Summary
    device_facts = result.get("device_facts", {})
    vlans = device_facts.get("vlans", [])
    interfaces = device_facts.get("interfaces", [])
    trunks = device_facts.get("trunks", [])
    
    output.append("\n📊 DEVICE STATE SUMMARY")
    output.append("-" * 120)
    output.append(f"VLANs Configured:       {len(vlans)}")
    output.append(f"Interfaces Found:       {len(interfaces)}")
    output.append(f"Trunk Ports:            {len(trunks)}")
    
    # Show relevant interfaces for the task
    if interfaces:
        output.append("\n📡 RELEVANT INTERFACES")
        output.append("-" * 120)
        output.append(f"{'Interface':<25} {'Status':<12} {'Mode':<12} {'VLAN':<10} {'Description':<30}")
        output.append("-" * 120)
        
        # Show interfaces mentioned in the workflow
        workflow_interfaces = set()
        for step in workflow:
            params = step.get("parameters", {})
            if "interface" in params:
                workflow_interfaces.add(params["interface"])
        
        # Show matching interfaces or first 5
        shown = 0
        for intf in interfaces:
            name = intf.get("name", "")
            
            # Check if this interface is mentioned in workflow
            is_relevant = any(
                wi in name or name in wi 
                for wi in workflow_interfaces
            )
            
            if is_relevant or shown < 5:
                status = intf.get("status", "unknown")
                mode = intf.get("mode", "unknown")
                vlan = intf.get("access_vlan", "N/A")
                desc = intf.get("description", "")[:30]
                
                output.append(f"{name:<25} {status:<12} {mode:<12} {str(vlan):<10} {desc:<30}")
                shown += 1
                
                if shown >= 10:
                    break
        
        if len(interfaces) > shown:
            output.append(f"\n... and {len(interfaces) - shown} more interfaces")
    
    # Show VLANs if any
    if vlans:
        output.append("\n🏷️  CONFIGURED VLANS")
        output.append("-" * 120)
        output.append(f"{'VLAN ID':<10} {'Name':<30} {'State':<15}")
        output.append("-" * 120)
        
        for vlan in vlans[:20]:  # Show first 20
            vlan_id = vlan.get("vlan_id", "N/A")
            name = vlan.get("name", "N/A")
            state = vlan.get("state", "N/A")
            output.append(f"{vlan_id:<10} {name:<30} {state:<15}")
        
        if len(vlans) > 20:
            output.append(f"\n... and {len(vlans) - 20} more VLANs")
    
    # Execution Status
    execution = result.get("execution", {})
    ready = execution.get("ready_for_execution", False)
    warnings = execution.get("warnings", [])
    
    output.append("\n✅ EXECUTION STATUS")
    output.append("-" * 120)
    
    if ready:
        output.append("Status:         ✓ READY FOR EXECUTION")
    else:
        output.append("Status:         ✗ NOT READY")
    
    if warnings:
        output.append(f"\nWarnings:       {len(warnings)}")
        for warning in warnings:
            output.append(f"  ⚠️  {warning}")
    else:
        output.append("Warnings:       None")
    
    # Footer
    output.append("\n" + "=" * 120)
    output.append("✓ ORCHESTRATION COMPLETE")
    output.append("=" * 120 + "\n")
    
    # Print to terminal
    print("\n".join(output))


def _display_error_result(result: dict):
    """Display error result"""
    
    output = []
    
    output.append("\n" + "=" * 120)
    output.append("ORCHESTRATION ERROR")
    output.append("=" * 120)
    
    error_type = result.get("error", "unknown_error")
    details = result.get("details", "No details available")
    
    output.append(f"\n✗ Error Type: {error_type.replace('_', ' ').title()}")
    output.append(f"\nDetails:")
    output.append(f"  {details}")
    
    output.append("\n" + "=" * 120 + "\n")
    
    # Print to terminal
    print("\n".join(output))
