import time
import asyncio
from fastapi import APIRouter, BackgroundTasks
import httpx
import logging
from config import github_client_id

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_token(device_code, interval, end_time) -> None:
    async with httpx.AsyncClient() as client:
        client.headers.update({"Accept": "application/json"})
        while time.time() < end_time:
            _response = await client.post(
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
                await asyncio.sleep(interval)
            else:
                logger.info(f"Token retrieved successfully: {_data}")
                return
        logger.warning("Device activation timed out.")


@router.get("/github-device-login")
async def authenticate(background_tasks: BackgroundTasks):
    async with httpx.AsyncClient() as client:
        client.headers.update({"Accept": "application/json"})
        _response = await client.post(
            "https://github.com/login/device/code",
            data={"client_id": github_client_id, "scope": "user:email"},
        )
    _response.raise_for_status()
    response_access = _response.json()
    end_time = time.time() + response_access["expires_in"]

    background_tasks.add_task(
        fetch_token,
        response_access["device_code"],
        response_access["interval"],
        end_time,
    )

    return {
        "message": "Authentication required.",
        "user_code": response_access["user_code"],
        "verification_uri": response_access["verification_uri"],
        "expires_at": end_time,
    }
