# language: Python 3.10+, file: exploit.py
# pip install aiohttp

import aiohttp
import asyncio
import os

TOKEN        = os.environ.get("TOKEN", "YOUR_TOKEN_HERE")
TARGET_HOURS = int(os.environ.get("HOURS", "5000"))
DELAY        = float(os.environ.get("DELAY", "0.5"))

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

MAX_DURATION   = 1800
TARGET_SECONDS = TARGET_HOURS * 3600
REQUESTS_NEEDED = TARGET_SECONDS // MAX_DURATION

async def fetch_games():
    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://discord.com/api/v10/applications/detectable",
            headers=HEADERS
        ) as r:
            return await r.json() if r.status == 200 else []

async def send_session(s, app_id, app_name, idx, total):
    body = {"application_id": app_id, "duration": MAX_DURATION}
    async with s.post(
        "https://discord.com/api/v9/activities",
        headers=HEADERS,
        json=body
    ) as r:
        status = r.status
        if status not in (200, 201, 204):
            txt = (await r.text())[:80]
            if "rate" in txt.lower():
                print(f"[!] ratelimit hit at {idx} — sleeping 10s")
                await asyncio.sleep(10)
                return False
            print(f"[!] {status} on {app_name}: {txt}")
        else:
            if idx % 100 == 0:
                hours_done = (idx * MAX_DURATION) / 3600
                print(f"[~] {idx}/{total} | {hours_done:.1f}h done | {app_name}")
        return True

async def main():
    print("[+] fetching game list...")
    games = await fetch_games()
    if not games:
        print("[-] failed to fetch games")
        return

    print(f"[+] {len(games)} games | target: {TARGET_HOURS}h = {REQUESTS_NEEDED} requests")

    async with aiohttp.ClientSession() as s:
        sent = 0
        # cycle through games repeatedly until target reached
        while sent < REQUESTS_NEEDED:
            for game in games:
                if sent >= REQUESTS_NEEDED:
                    break
                ok = await send_session(s, game["id"], game["name"], sent, REQUESTS_NEEDED)
                if ok:
                    sent += 1
                await asyncio.sleep(DELAY)

    print(f"[+] done — {sent * MAX_DURATION / 3600:.1f}h submitted")

asyncio.run(main())
