"""
Test raw LLM intent extraction independently
"""

import json

from app.services.intent_service import (
    parse_intent
)


# =====================================================
# SAMPLE TASK
# =====================================================

sample_task = """
Create VLAN 110 named FINANCE_USERS.

Configure interfaces Gi1/0/5 and Gi1/0/6
as access ports.

Assign VLAN 110 to Gi1/0/5 and Gi1/0/6.

Configure interface Gi1/0/24 as trunk port.

Allow VLANs 110,200 on Gi1/0/24.

Configure native VLAN 999 on Gi1/0/24.

Shutdown interface Gi1/0/20.

Save configuration.
"""


# =====================================================
# TEST START
# =====================================================

print("\n" + "=" * 80)

print("TESTING LLM INTENT EXTRACTION")

print("=" * 80)

print("\nINPUT TASK:\n")

print(sample_task)

print("\n" + "=" * 80)

print("LLM RESPONSE")

print("=" * 80)


# =====================================================
# RUN INTENT EXTRACTION
# =====================================================

result = parse_intent(
    sample_task
)


# =====================================================
# PRINT OUTPUT
# =====================================================

print(

    json.dumps(
        result,
        indent=4
    )
)

print("\n" + "=" * 80)

print("TEST COMPLETE")

print("=" * 80)