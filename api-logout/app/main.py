import os

import httpx
import jwt
from fastapi import FastAPI, Header, HTTPException

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8001")
PEER_BACKEND_URL = os.environ.get("PEER_BACKEND_URL", "")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "")

app = FastAPI(title="webstore-api-logout")


def _backend_urls() -> list[str]:
    urls = [BACKEND_URL]
    if PEER_BACKEND_URL and PEER_BACKEND_URL not in urls:
        urls.append(PEER_BACKEND_URL)
    return urls


def backend_json(method: str, path: str) -> httpx.Response:
    headers = {"X-Internal-Token": INTERNAL_TOKEN}
    last: Exception | None = None
    for base in _backend_urls():
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.request(method, f"{base}{path}", headers=headers)
            if response.status_code < 500:
                return response
            last = RuntimeError(response.text)
        except Exception as exc:
            last = exc
            continue
    raise HTTPException(status_code=503, detail=f"backend unreachable: {last}")


def sid_from_auth(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    sid = payload.get("sid")
    if not sid:
        raise HTTPException(status_code=401, detail="token missing sid")
    return sid


@app.get("/healthz")
def healthz() -> dict:
    response = backend_json("GET", "/healthz")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="backend unhealthy")
    return {"ok": True}


@app.post("/api/logout")
def logout(authorization: str | None = Header(default=None)) -> dict:
    sid = sid_from_auth(authorization)
    response = backend_json("DELETE", f"/internal/sessions/{sid}")
    if response.status_code not in (200, 404):
        raise HTTPException(status_code=502, detail=response.text)
    return {"ok": True}
