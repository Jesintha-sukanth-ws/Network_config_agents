import requests
from config.settings import DEVICE_CREDENTIALS

url = "https://devnetsandboxiosxec9k.cisco.com/restconf/data"

headers = {
    "Accept": "application/yang-data+json"
}

cisco_creds = DEVICE_CREDENTIALS.get("Cisco", {})
username = cisco_creds.get("username", "")
password = cisco_creds.get("password", "")

response = requests.get(
    url,
    auth=(username, password),
    headers=headers,
    verify=False
)

print(response.status_code)
print(response.text)