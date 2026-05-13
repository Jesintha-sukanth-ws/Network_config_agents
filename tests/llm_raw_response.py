"""
Test file to inspect raw Ollama LLM response structure

Purpose:
- See full response before extraction
- Understand message/content hierarchy
- Understand how workflow JSON is extracted
"""

import json
import ollama

# =====================================================
# SIMPLE SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """
You are a network automation assistant.
Always return valid JSON.
"""

# =====================================================
# SAMPLE USER TASK
# =====================================================

user_task = "Create VLAN 10 and assign it to GigabitEthernet0/1"

# =====================================================
# SEND REQUEST TO OLLAMA
# =====================================================

response = ollama.chat(
    model="gpt-oss:120b-cloud",
    messages=[
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_task
        }
    ]
)

# =====================================================
# STEP 1 — PRINT FULL RESPONSE
# =====================================================

print("\n" + "=" * 80)
print("FULL RESPONSE OBJECT")
print("=" * 80)
print(response)

# =====================================================
# STEP 2 — PRINT RESPONSE TYPE
# =====================================================

print("\n" + "=" * 80)
print("RESPONSE TYPE")
print("=" * 80)
print(type(response))

# =====================================================
# STEP 3 — PRINT RESPONSE KEYS
# =====================================================

print("\n" + "=" * 80)
print("TOP LEVEL KEYS")
print("=" * 80)
print(response.keys())

# =====================================================
# STEP 4 — EXTRACT MESSAGE OBJECT
# =====================================================

message = response["message"]

print("\n" + "=" * 80)
print("MESSAGE OBJECT")
print("=" * 80)
print(message)

# =====================================================
# STEP 5 — EXTRACT CONTENT
# =====================================================

content = response["message"]["content"]

print("\n" + "=" * 80)
print("CONTENT ONLY")
print("=" * 80)
print(content)

# =====================================================
# STEP 6 — CONTENT TYPE
# =====================================================

print("\n" + "=" * 80)
print("CONTENT TYPE")
print("=" * 80)
print(type(content))

# =====================================================
# STEP 7 — CONVERT JSON STRING TO PYTHON DICTIONARY
# =====================================================

try:
    parsed_json = json.loads(content)

    print("\n" + "=" * 80)
    print("PARSED JSON")
    print("=" * 80)
    print(parsed_json)

    print("\n" + "=" * 80)
    print("PARSED JSON TYPE")
    print("=" * 80)
    print(type(parsed_json))

except json.JSONDecodeError as e:

    print("\nJSON PARSING FAILED")
    print(e)

# =====================================================
# STEP 8 — ACCESS WORKFLOW
# =====================================================

if 'parsed_json' in locals():

    workflow = parsed_json.get("workflow")

    print("\n" + "=" * 80)
    print("WORKFLOW ONLY")
    print("=" * 80)
    print(workflow)

# =====================================================
# FINAL FLOW EXPLANATION
# =====================================================

print("\n" + "=" * 80)
print("FLOW SUMMARY")
print("=" * 80)

print("""
1. Ollama returns FULL response object
2. Workflow exists inside response['message']['content']
3. Content is still STRING data
4. json.loads() converts string → Python dictionary
5. Workflow is extracted from parsed JSON
""")
