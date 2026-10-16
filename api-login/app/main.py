import os
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import FastAPI, HTTPException
from ldap3 import ALL, Connection, Server
from pydantic import BaseModel, Field

LDAP_URL = os.environ.get("LDAP_URL", "ldap://host.containers.internal:389")
LDAP_PEER_URL = os.environ.get("LDAP_PEER_URL", "")
PEOPLE_OU = os.environ.get("LDAP_PEOPLE_OU", "ou=People,dc=webstore,dc=local")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8001")
PEER_BACKEND_URL = os.environ.get("PEER_BACKEND_URL", "")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "30"))

app = FastAPI(title="webstore-api-login")


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


def _ldap_urls() -> list[str]:
    urls = [LDAP_URL]
    if LDAP_PEER_URL and LDAP_PEER_URL not in urls:
        urls.append(LDAP_PEER_URL)
    return urls


def _backend_urls() -> list[str]:
    urls = [BACKEND_URL]
    if PEER_BACKEND_URL and PEER_BACKEND_URL not in urls:
        urls.append(PEER_BACKEND_URL)
    return urls


def ldap_bind_user(username: str, password: str) -> bool:
    dn = f"uid={username},{PEOPLE_OU}"
    for url in _ldap_urls():
        try:
            server = Server(url, get_info=ALL, connect_timeout=3)
            conn = Connection(
                server,
                user=dn,
                password=password,
                auto_bind=True,
                receive_timeout=5,
            )
            conn.unbind()
            return True
        except Exception:
            continue
    return False


def ldap_reachable() -> bool:
    for url in _ldap_urls():
        try:
            server = Server(url, connect_timeout=2)
            if server.check_availability():
                return True
        except Exception:
            continue
    return False


def backend_json(method: str, path: str, json: dict | None = None) -> httpx.Response:
    headers = {"X-Internal-Token": INTERNAL_TOKEN}
    last: Exception | None = None
    for base in _backend_urls():
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.request(method, f"{base}{path}", json=json, headers=headers)
            if response.status_code < 500:
                return response
            last = RuntimeError(response.text)
        except Exception as exc:
            last = exc
            continue
    raise HTTPException(status_code=503, detail=f"backend unreachable: {last}")


@app.get("/healthz")
def healthz() -> dict:
    if not ldap_reachable():
        raise HTTPException(status_code=503, detail="ldap unreachable")
    response = backend_json("GET", "/healthz")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="backend unhealthy")
    return {"ok": True}


@app.post("/api/login")
def login(body: LoginIn) -> dict:
    username = body.username.strip()
    if not ldap_bind_user(username, body.password):
        raise HTTPException(status_code=401, detail="invalid credentials")
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="jwt secret missing")
    created = backend_json("POST", "/internal/sessions", json={"uid": username})
    if created.status_code != 200:
        raise HTTPException(status_code=502, detail=created.text)
    sid = created.json()["sid"]
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": username,
            "sid": sid,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=JWT_EXPIRE_MINUTES)).timestamp()),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"token": token}
