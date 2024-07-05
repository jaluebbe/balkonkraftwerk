import time
import logging
import requests
from config import github_client_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_token_via_device_flow():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    _response = session.post(
        "https://github.com/login/device/code",
        data={"client_id": github_client_id, "scope": "user:email"},
    )
    _response.raise_for_status()
    response_access = _response.json()
    device_code = response_access["device_code"]
    user_code = response_access["user_code"]
    verification_uri = response_access["verification_uri"]
    interval = response_access["interval"]
    expires_in = response_access["expires_in"]
    logger.info(
        f"Enter the user code '{user_code}' on {verification_uri} within "
        f"{expires_in} seconds."
    )
    end_time = time.time() + expires_in
    while time.time() < end_time:
        _response = session.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": github_client_id,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            },
            headers={"Accept": "application/json"},
        )
        _response.raise_for_status()
        _data = _response.json()
        if _data.get("error") == "authorization_pending":
            time.sleep(interval)
        else:
            return _data
    logger.warning("Device activation timed out.")


if __name__ == "__main__":
    token_info = get_token_via_device_flow()
    if token_info:
        logger.info(token_info)
    else:
        logger.error("Failed to retrieve token.")
