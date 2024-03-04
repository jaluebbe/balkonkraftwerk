import os
import httpx
from fastapi import Request, APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()

github_client_id = os.environ["GITHUB_CLIENT_ID"]
github_client_secret = os.environ["GITHUB_CLIENT_SECRET"]
github_star_repo = os.environ["GITHUB_STAR_REPO"]


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
    headers.update({"Authorization": f"Bearer {access_token}"})
    async with httpx.AsyncClient() as client:
        response_email = await client.get(
            "https://api.github.com/user/emails", headers=headers
        )
        if github_star_repo is not None:
            response_starred = await client.get(
                f"https://api.github.com/user/starred/{github_star_repo}",
                headers=headers,
            )
    email = [
        _item["email"]
        for _item in response_email.json()
        if _item["primary"] == True
    ][0]
    if github_star_repo is None or response_starred.status_code == 204:
        request.session["user"] = email
    return RedirectResponse("/")
