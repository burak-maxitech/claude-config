import os

import yaml
from fastapi import FastAPI

from app.crypto import encrypt
from app.images import parse_timestamp
from app.utils import current_iso

app = FastAPI()

CONFIG = yaml.safe_load(open("config.yaml")) if os.path.exists("config.yaml") else {}
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
SECRET_KEY = os.environ["SECRET_KEY"]


@app.get("/")
def index():
    return {"db": DATABASE_URL, "now": current_iso(), "config": CONFIG}


@app.get("/parse")
def parse(ts: str):
    return {"parsed": parse_timestamp(ts).isoformat()}


@app.post("/seal")
def seal(payload: str):
    token = encrypt(payload.encode(), SECRET_KEY.encode().ljust(16, b"0")[:16])
    return {"len": len(token)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
