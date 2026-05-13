import requests
from config.settings import USERNAME ,PASSWORD

url = "https://devnetsandboxiosxec9k.cisco.com/restconf/data"

headers = {
    "Accept": "application/yang-data+json"
}

response = requests.get(
    url,
    auth=("username", "password"),
    headers=headers,
    verify=False
)

print(response.status_code)
print(response.text)