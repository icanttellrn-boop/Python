# language: Python 3.10+, file: exploit.py
# pip install discord.py-self aiohttp

import discord
import aiohttp
import asyncio
import os
import random

TOKEN      = os.environ.get("TOKEN", "YOUR_TOKEN_HERE")
MODE       = os.environ.get("MODE", "both")   # variety | hours | both
DELAY      = float(os.environ.get("DELAY", "1.5"))  # seconds between game switches

client = discord.Client()
games_cache = []

async def fetch_detectable(token):
    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://discord.com/api/v10/applications/detectable",
            headers={"Authorization": token}
        ) as r:
            if r.status == 200:
                return await r.json()
    return []

async def set_game(game):
    try:
        await client.ws.send_as_json({
            "op": 3,
            "d": {
                "since": None,
                "activities": [{
                    "type": 0,
                    "name": game["name"],
                    "application_id": game["id"],
                    "flags": 0,
                }],
                "status": "online",
                "afk": False,
            }
        })
    except Exception as e:
        print(f"[!] ws error: {e}")

async def clear_presence():
    try:
        await client.ws.send_as_json({
            "op": 3,
            "d": {
                "since": None,
                "activities": [],
                "status": "online",
                "afk": False,
            }
        })
    except Exception:
        pass

async def farm_variety():
    """cycle every unique game — each transition = 1 game counted"""
    total = len(games_cache)
    print(f"[+] variety farm — {total} games to cycle")
    for i, game in enumerate(games_cache):
        await set_game(game)
        await asyncio.sleep(DELAY)
        await clear_presence()
        await asyncio.sleep(0.3)
        if i % 50 == 0:
            print(f"[~] {i}/{total} — {game['name']}")
    print("[+] variety cycle done")

async def farm_hours():
    """loop one game — accumulates time server-side"""
    if not games_cache:
        return
    game = games_cache[0]
    print(f"[+] hours farm — {game['name']}")
    while True:
        await set_game(game)
        await asyncio.sleep(60)

async def farm_both():
    """cycle all games for variety, loop back for hours"""
    total = len(games_cache)
    print(f"[+] full farm — {total} games")
    seen = set()
    while True:
        for i, game in enumerate(games_cache):
            await set_game(game)
            await asyncio.sleep(DELAY)
            if game["id"] not in seen:
                seen.add(game["id"])
                await clear_presence()
                await asyncio.sleep(0.3)
            if i % 100 == 0:
                print(f"[~] {i}/{total} | unique: {len(seen)}")

@client.event
async def on_ready():
    global games_cache
    print(f"[+] {client.user}")
    games_cache = await fetch_detectable(TOKEN)
    random.shuffle(games_cache)
    print(f"[+] loaded {len(games_cache)} detectable games")

    if   MODE == "variety": asyncio.ensure_future(farm_variety())
    elif MODE == "hours":   asyncio.ensure_future(farm_hours())
    else:                   asyncio.ensure_future(farm_both())

@client.event
async def on_resumed():
    print("[~] reconnected")

client.run(TOKEN)
