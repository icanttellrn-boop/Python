# language: Python 3.10+, file: exploit.py
# pip install aiohttp

import aiohttp
import asyncio
import os

TOKEN = os.environ.get("TOKEN", "YOUR_TOKEN_HERE")
TARGET_HOURS = int(os.environ.get("HOURS", "5000"))

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

APP_ID = "356875221078245376"  # minecraft

# try different duration sizes to find the max
TEST_DURATIONS = [
    3600,         # 1h
    86400,        # 1 day
    604800,       # 1 week
    2592000,      # 30 days
    31536000,     # 1 year
    2147483647,   # int32 max
]

BODY_VARIANTS = [
    lambda d: {"application_id": APP_ID, "duration": d},
    lambda d: {"application_id": APP_ID, "duration": d, "session_id": "0"},
    lambda d: {"application_id": APP_ID, "duration": d, "game_name": "Minecraft"},
    lambda d: {"application_id": int(APP_ID), "duration": d},
]

async def probe_body():
    async with aiohttp.ClientSession() as s:
        print("[~] probing body shape + max duration")
        for body_fn in BODY_VARIANTS:
            body = body_fn(3600)
            async with s.post(
                "https://discord.com/api/v9/activities",
                headers=HEADERS, json=body
            ) as r:
                txt = (await r.text())[:200]
                print(f"[{r.status}] {body} => {txt}")
            await asyncio.sleep(1)

        print("\n[~] probing max duration")
        for d in TEST_DURATIONS:
            body = {"application_id": APP_ID, "duration": d}
            async with s.post(
                "https://discord.com/api/v9/activities",
                headers=HEADERS, json=body
            ) as r:
                txt = (await r.text())[:200]
                print(f"[{r.status}] duration={d} => {txt}")
            await asyncio.sleep(1)

async def check_stats():
    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://discord.com/api/v9/users/@me/activities/statistics/applications",
            headers=HEADERS
        ) as r:
            print(f"\n[stats] {await r.text()}")

async def main():
    await probe_body()
    await check_stats()

asyncio.run(main())
