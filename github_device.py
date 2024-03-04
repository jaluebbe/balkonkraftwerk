import requests
from config import github_client_id

session = requests.Session()
session.headers.update({"Accept": "application/json"})
_response = session.post(
    "https://github.com/login/device/code",
    data={"client_id": github_client_id, "scope": "user:email"},
)
response_access = _response.json()
device_code = response_access["device_code"]
user_code = response_access["user_code"]
verification_uri = response_access["verification_uri"]
input(
    f"Enter the user code '{user_code}' on {verification_uri}"
    " within 15 minutes before pressing 'Enter':"
)
_response = session.post(
    "https://github.com/login/oauth/access_token",
    data={
        "client_id": github_client_id,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": device_code,
    },
    headers={"Accept": "application/json"},
)
response_token = _response.json()
print(response_token)
