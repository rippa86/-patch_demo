import os

import httpx
import jwt
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8001")
PEER_BACKEND_URL = os.environ.get("PEER_BACKEND_URL", "")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "")

app = FastAPI(title="webstore-api-cart")


class CartIn(BaseModel):
    items: list[dict]


def _backend_urls() -> list[str]:
    urls = [BACKEND_URL]
    if PEER_BACKEND_URL and PEER_BACKEND_URL not in urls:
        urls.append(PEER_BACKEND_URL)
    return urls


def backend_json(
    method: str, path: str, json: dict | None = None, params: dict | None = None
) -> httpx.Response:
    headers = {"X-Internal-Token": INTERNAL_TOKEN}
    last: Exception | None = None
    for base in _backend_urls():
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.request(
                    method, f"{base}{path}", json=json, params=params, headers=headers
                )
            if response.status_code < 500:
                return response
            last = RuntimeError(response.text)
        except Exception as exc:
            last = exc
            continue
    raise HTTPException(status_code=503, detail=f"backend unreachable: {last}")


def identity(authorization: str | None) -> tuple[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    uid = payload.get("sub")
    sid = payload.get("sid")
    if not uid or not sid:
        raise HTTPException(status_code=401, detail="token missing claims")
    check = backend_json("GET", f"/internal/sessions/{sid}")
    if check.status_code != 200:
        raise HTTPException(status_code=401, detail="session invalid")
    if check.json().get("uid") != uid:
        raise HTTPException(status_code=401, detail="session mismatch")
    return uid, sid


@app.get("/healthz")
def healthz() -> dict:
    response = backend_json("GET", "/healthz")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="backend unhealthy")
    return {"ok": True}


@app.get("/api/cart/products")
def products() -> list:
    response = backend_json("GET", "/internal/products")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=response.text)
    return response.json()


@app.get("/api/cart")
def get_cart(authorization: str | None = Header(default=None)) -> dict:
    uid, _ = identity(authorization)
    response = backend_json("GET", "/internal/cart", params={"uid": uid})
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=response.text)
    return response.json()


@app.put("/api/cart")
def put_cart(body: CartIn, authorization: str | None = Header(default=None)) -> dict:
    uid, _ = identity(authorization)
    response = backend_json(
        "PUT", "/internal/cart", json={"uid": uid, "items": body.items}
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.post("/api/cart/checkout")
def checkout(authorization: str | None = Header(default=None)) -> dict:
    uid, _ = identity(authorization)
    response = backend_json("POST", "/internal/orders", json={"uid": uid})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()
