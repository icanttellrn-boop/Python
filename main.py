# language: Python 3.10+, file: farm.py
# pip install discord.py-self aiohttp

import discord
import aiohttp
import asyncio
import os
import json

TOKEN    = os.environ.get("TOKEN", "YOUR_TOKEN_HERE")
GAME_KEY = os.environ.get("GAME", "counter-strike")   # поисковая строка

client = discord.Client()
chosen_game = None

async def fetch_detectable(token: str) -> list:
    """тянем актуальный список игр прямо с апи дискорда — иконки гарантированы"""
    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://discord.com/api/v10/applications/detectable",
            headers={"Authorization": token}
        ) as r:
            if r.status != 200:
                print(f"[-] detectable fetch failed: {r.status}")
                return []
            return await r.json()

def find_game(games: list, query: str) -> dict | None:
    q = query.lower()
    # точное совпадение сначала
    for g in games:
        if g.get("name", "").lower() == q:
            return g
    # частичное
    for g in games:
        if q in g.get("name", "").lower():
            return g
    return None

async def push_presence(game: dict):
    """raw gateway payload — application_id из базы дискорда"""
    payload = {
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
    }
    await client.ws.send_as_json(payload)

@client.event
async def on_ready():
    global chosen_game
    print(f"[+] logged in as {client.user}")

    games = await fetch_detectable(TOKEN)
    if not games:
        print("[-] couldn't fetch game list")
        return

    chosen_game = find_game(games, GAME_KEY)
    if not chosen_game:
        print(f"[-] game not found: {GAME_KEY}")
        print("[i] available (sample):", [g["name"] for g in games[:10]])
        return

    print(f"[+] farming: {chosen_game['name']} (id={chosen_game['id']})")
    await push_presence(chosen_game)

@client.event
async def on_resumed():
    if chosen_game:
        await push_presence(chosen_game)
        print("[~] resumed — presence restored")

@client.event
async def on_connect():
    if chosen_game:
        await push_presence(chosen_game)

client.run(TOKEN)
