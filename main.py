# language: Python 3.10+, file: exploit.py
# pip install aiohttp

import aiohttp
import asyncio
import os

TOKEN = os.environ.get("TOKEN", "YOUR_TOKEN_HERE")
HOURS = int(os.environ.get("HOURS", "5000"))

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36",
}

async def fetch_detectable():
    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://discord.com/api/v10/applications/detectable",
            headers=HEADERS
        ) as r:
            return await r.json() if r.status == 200 else []

async def get_current_stats(app_id):
    async with aiohttp.ClientSession() as s:
        async with s.get(
            f"https://discord.com/api/v10/users/@me/applications/{app_id}/stats",
            headers=HEADERS
        ) as r:
            print(f"  GET stats {r.status}: {await r.text()}")

async def try_post_stats(app_id, app_name, duration_seconds):
    payloads = [
        {"duration": duration_seconds},
        {"total_duration": duration_seconds},
        {"time": duration_seconds},
        {"playtime": duration_seconds},
        {"seconds": duration_seconds},
    ]
    async with aiohttp.ClientSession() as s:
        for body in payloads:
            async with s.post(
                f"https://discord.com/api/v10/users/@me/applications/{app_id}/stats",
                headers=HEADERS,
                json=body
            ) as r:
                txt = await r.text()
                print(f"  POST {app_name} | body={body} | {r.status}: {txt[:80]}")
                if r.status in (200, 201, 204):
                    print(f"  [!!] HIT — {body}")
                    return True
                await asyncio.sleep(0.3)
    return False

async def main():
    print("[+] fetching games...")
    games = await fetch_detectable()
    if not games:
        print("[-] no games fetched")
        return

    duration = HOURS * 3600
    print(f"[+] {len(games)} games | target: {HOURS}h = {duration}s")

    # probe first game to see endpoint structure
    g = games[0]
    print(f"\n[~] probing {g['name']} ({g['id']})")
    await get_current_stats(g["id"])
    await try_post_stats(g["id"], g["name"], duration)

asyncio.run(main())
