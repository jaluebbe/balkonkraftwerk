from fastapi import Request, HTTPException


def requires_auth(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="unidentified user")
    return request
