import asyncio
import logging
import os
import random

import httpx

STORE_BASE_URL = os.environ.get("STORE_BASE_URL", "http://shoppingapp.lab.rippa.io").rstrip("/")
SYNTH_COUNT = int(os.environ.get("SYNTH_COUNT", "100"))
SYNTH_MIN_SEC = float(os.environ.get("SYNTH_MIN_SEC", "15"))
SYNTH_MAX_SEC = float(os.environ.get("SYNTH_MAX_SEC", "45"))
SYNTH_PASSWORD = os.environ.get("SYNTH_PASSWORD", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("synth-users")


async def ensure_account(client: httpx.AsyncClient, username: str) -> None:
    response = await client.post(
        f"{STORE_BASE_URL}/api/account",
        json={
            "username": username,
            "password": SYNTH_PASSWORD,
            "email": f"{username}@lab.rippa.io",
        },
        timeout=10.0,
    )
    if response.status_code in (200, 201, 409):
        return
    log.warning("create %s -> %s %s", username, response.status_code, response.text)


async def run_user(n: int) -> None:
    username = f"synth{n:03d}"
    token = None
    async with httpx.AsyncClient() as client:
        await ensure_account(client, username)
        await asyncio.sleep(random.uniform(0, SYNTH_MAX_SEC))
        while True:
            await asyncio.sleep(random.uniform(SYNTH_MIN_SEC, SYNTH_MAX_SEC))
            try:
                if token is None:
                    response = await client.post(
                        f"{STORE_BASE_URL}/api/login",
                        json={"username": username, "password": SYNTH_PASSWORD},
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    token = response.json()["token"]
                    log.info("%s login", username)
                else:
                    response = await client.post(
                        f"{STORE_BASE_URL}/api/logout",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10.0,
                    )
                    if response.status_code < 500:
                        log.info("%s logout", username)
                        token = None
                    else:
                        token = None
            except Exception as exc:
                log.warning("%s error: %s", username, exc)
                token = None


async def main() -> None:
    if not SYNTH_PASSWORD:
        raise SystemExit("SYNTH_PASSWORD is required")
    log.info(
        "starting %s users against %s interval %.0f-%.0fs",
        SYNTH_COUNT,
        STORE_BASE_URL,
        SYNTH_MIN_SEC,
        SYNTH_MAX_SEC,
    )
    await asyncio.gather(*(run_user(n) for n in range(1, SYNTH_COUNT + 1)))


if __name__ == "__main__":
    asyncio.run(main())
