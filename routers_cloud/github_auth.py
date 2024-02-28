import os
import httpx
from fastapi import Request, APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()

github_client_id = os.environ["GITHUB_CLIENT_ID"]
github_client_secret = os.environ["GITHUB_CLIENT_SECRET"]


@router.get("/github-login")
async def github_login():
    return RedirectResponse(
        "https://github.com/login/oauth/authorize?"
        f"client_id={github_client_id}&scope=user:email",
        status_code=302,
    )


@router.get("/github-code")
async def github_code(request: Request, code: str):
    params = {
        "client_id": github_client_id,
        "client_secret": github_client_secret,
        "code": code,
    }
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url="https://github.com/login/oauth/access_token",
            params=params,
            headers=headers,
        )
    response_json = response.json()
    access_token = response_json["access_token"]
    async with httpx.AsyncClient() as client:
        headers.update({"Authorization": f"Bearer {access_token}"})
        response = await client.get(
            "https://api.github.com/user/emails", headers=headers
        )
    email = [
        _item["email"] for _item in response.json() if _item["primary"] == True
    ][0]
    request.session["user"] = email
    return RedirectResponse("/")
