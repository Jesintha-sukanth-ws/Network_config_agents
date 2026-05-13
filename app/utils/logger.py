"""
Orchestration Logger

Centralized logging and formatting for orchestration workflow.
Provides consistent formatting for:
- Orchestration progress tracking
- Validation results
- Device facts display
- Execution plan summaries
"""


class OrchestrationLogger:
    """
    Handles all orchestration progress logging with consistent formatting.
    """

    @staticmethod
    def step_start(step_number, total_steps, step_name):
        """Log the start of an orchestration step"""
        print(f"\n[{step_number}/{total_steps}] {step_name}...")

    @staticmethod
    def step_progress(message):
        """Log progress within a step"""
        print(f"  → {message}")

    @staticmethod
    def step_success(message):
        """Log successful step completion"""
        print(f"   {message}")

    @staticmethod
    def step_failure(message):
        """Log step failure"""
        print(f"   {message}")

    @staticmethod
    def step_info(message):
        """Log informational message"""
        print(f"   {message}")

    @staticmethod
    def step_detail(message):
        """Log detailed information (indented)"""
        print(f"    - {message}")

    @staticmethod
    def header(title):
        """Log section header"""
        print(f"\n{'=' * 80}")
        print(title)
        print(f"{'=' * 80}")

    @staticmethod
    def subheader(title):
        """Log subsection header"""
        print(f"\n{title}\n")

    @staticmethod
    def validation_start(validation_type):
        """Log start of validation with sub-checks"""
        print(f"\n[Validation] {validation_type}...")

    @staticmethod
    def validation_check(check_name):
        """Log individual validation check"""
        print(f"  → Checking {check_name}...")

    @staticmethod
    def validation_passed(validation_type, details=None):
        """Log successful validation"""
        print(f"   {validation_type} PASSED")
        if details:
            for detail in details:
                print(f"   {detail}")

    @staticmethod
    def validation_failed(validation_type, error_count, errors=None):
        """Log failed validation with errors"""
        print(f"  ✗ {validation_type} FAILED")
        print(f"  ✗ Found {error_count} error(s)")
        if errors:
            for idx, error in enumerate(errors[:3], 1):
                msg = error.get('message', 'Unknown error') if isinstance(error, dict) else str(error)
                print(f"    {idx}. {msg}")
            if len(errors) > 3:
                print(f"    ... and {len(errors) - 3} more error(s)")

    @staticmethod
    def execution_plan(total_steps, execute_count, skip_count, skip_reasons=None):
        """Log execution plan summary"""
        print(f"  ✓ Execution plan created: {total_steps} step(s)")
        print(f"    - Steps to execute: {execute_count}")
        print(f"    - Steps to skip: {skip_count} (already configured)")
        
        if skip_reasons and skip_count > 0:
            print("  ℹ Skip reasons:")
            for reason in skip_reasons:
                print(f"    - {reason}")

    # =====================================================
    # DEVICE FACTS FORMATTING
    # =====================================================

    @staticmethod
    def format_device_summary(device_facts):
        """Format and display device summary"""
        device_info = device_facts.get("device_info", {})
        hostname = device_info.get("hostname", "Unknown")
        os_version = device_info.get("os_version", "Unknown")

        print("\nDEVICE SUMMARY")
        print("-" * 50)
        print(f"Hostname      : {hostname}")
        print(f"OS Version    : {os_version}")

    @staticmethod
    def format_vlan_summary(device_facts):
        """Format and display VLAN summary"""
        vlans = device_facts.get("vlans", [])

        print("\nVLAN SUMMARY")
        print("-" * 50)

        if not vlans:
            print("No VLANs found")
            return

        print(f"{'VLAN ID':<12}{'Name':<25}")
        print("-" * 50)

        for vlan in vlans:
            vlan_id = vlan.get("vlan_id", "-")
            name = vlan.get("name", "-")
            print(f"{str(vlan_id):<12}{name:<25}")

    @staticmethod
    def format_interface_summary(device_facts):
        """Format and display interface summary"""
        interfaces = device_facts.get("interfaces", [])

        print("\nINTERFACE SUMMARY")
        print("-" * 90)
        print(f"{'Interface':<18}{'Status':<12}{'Mode':<12}{'Access VLAN':<15}{'Description':<25}")
        print("-" * 90)

        for interface in interfaces:
            name = interface.get("name", "-")
            status = interface.get("status", "-")
            mode = interface.get("mode", "-")
            access_vlan = interface.get("access_vlan", "-")
            description = interface.get("description", "-")
            
            print(f"{name:<18}{status:<12}{mode:<12}{str(access_vlan):<15}{description:<25}")

    @staticmethod
    def format_trunk_summary(device_facts):
        """Format and display trunk summary"""
        trunks = device_facts.get("trunks", [])

        print("\nTRUNK SUMMARY")
        print("-" * 80)

        if not trunks:
            print("No trunk interfaces found")
            return

        print(f"{'Interface':<18}{'Native VLAN':<18}{'Allowed VLANs'}")
        print("-" * 80)

        for trunk in trunks:
            interface = trunk.get("interface", "-")
            native_vlan = trunk.get("native_vlan", "-")
            allowed_vlans = trunk.get("allowed_vlans", [])
            vlan_text = ",".join(map(str, allowed_vlans))
            
            print(f"{interface:<18}{str(native_vlan):<18}{vlan_text}")


# Singleton instance
logger = OrchestrationLogger()
