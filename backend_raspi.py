#!venv/bin/python3
import os
import time
from pathlib import Path
import socket
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from redis import asyncio as aioredis

import routers_raspi.datasets as datasets
import routers_raspi.review as review
import routers_raspi.meters as meters

hostname = socket.gethostname()
if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
log_directory = Path("../logs_json")
if not log_directory.is_dir():
    log_directory.mkdir()
app.mount("/archive", StaticFiles(directory=log_directory), name="archive")

app.include_router(datasets.router)
app.include_router(review.router)
app.include_router(meters.router)


@app.get("/", include_in_schema=False)
async def root(request: Request):
    return RedirectResponse("/static/index.html")


@app.get("/api/current_power")
async def get_current_power():
    _key = "power:{}:{}".format(hostname, time.strftime("%Y%m%d"))
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    _data = await redis_connection.lrange(_key, 0, 0)
    if len(_data) == 0:
        raise HTTPException(status_code=404, detail="no data available")
    return Response(content=_data[0], media_type="application/json")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
