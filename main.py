# language: Python 3.10+, file: probe.py
# pip install aiohttp

import aiohttp
import asyncio
import os

TOKEN = os.environ.get("TOKEN", "YOUR_TOKEN_HERE")

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

APP_ID   = "356875221078245376"  # minecraft
DURATION = 18000000  # 5000 hours in seconds

ENDPOINTS = [
    ("GET",   "/api/v9/users/@me/activities/statistics/applications"),
    ("POST",  "/api/v9/users/@me/activities/statistics/applications"),
    ("POST",  f"/api/v9/users/@me/activities/statistics/applications/{APP_ID}"),
    ("PUT",   f"/api/v9/users/@me/activities/statistics/applications/{APP_ID}"),
    ("PATCH", f"/api/v9/users/@me/activities/statistics/applications/{APP_ID}"),
    ("POST",  "/api/v9/users/@me/activities"),
    ("POST",  f"/api/v9/users/@me/applications/{APP_ID}/stats"),
    ("GET",   f"/api/v9/users/@me/applications/{APP_ID}/stats"),
    ("POST",  f"/api/v9/applications/{APP_ID}/stats"),
    ("POST",  "/api/v9/users/@me/game-sessions"),
    ("POST",  f"/api/v9/users/@me/game-sessions/{APP_ID}"),
    ("POST",  "/api/v10/users/@me/activities"),
    ("GET",   "/api/v9/users/@me/activities/statistics/applications"),
    ("POST",  "/api/v9/activities"),
]

BODY = {
    "application_id": APP_ID,
    "duration": DURATION,
    "total_duration": DURATION,
    "sessions": 1,
}

async def probe():
    base = "https://discord.com"
    async with aiohttp.ClientSession() as s:
        for method, path in ENDPOINTS:
            try:
                fn = getattr(s, method.lower())
                kwargs = {"headers": HEADERS}
                if method in ("POST", "PUT", "PATCH"):
                    kwargs["json"] = BODY
                async with fn(base + path, **kwargs) as r:
                    txt = (await r.text())[:120]
                    print(f"[{r.status}] {method} {path}")
                    if r.status not in (404, 405):
                        print(f"      >> {txt}")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[ERR] {method} {path} — {e}")

asyncio.run(probe())
