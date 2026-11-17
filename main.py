# language: Python 3.10+, file: farm.py
# pip install discord.py-self

import discord
import asyncio
import os

TOKEN    = os.environ.get("TOKEN", "YOUR_TOKEN_HERE")
GAME_KEY = os.environ.get("GAME", "minecraft")

GAMES = {
    "minecraft": ("Minecraft",         356875221078245376),
    "league":    ("League of Legends", 401518684763136010),
    "valorant":  ("VALORANT",          700136079562375258),
    "roblox":    ("Roblox",            363445589247131668),
    "fortnite":  ("Fortnite",          432980957394370572),
    "apex":      ("Apex Legends",      771112077137379338),
    "csgo":      ("Counter-Strike 2",  730877295465693264),
}

name, app_id = GAMES.get(GAME_KEY, GAMES["minecraft"])

ACTIVITY = discord.Activity(
    type=discord.ActivityType.playing,
    name=name,
    application_id=app_id,
)

client = discord.Client()

async def push_presence():
    await client.change_presence(
        status=discord.Status.online,
        activity=ACTIVITY,
    )

@client.event
async def on_ready():
    print(f"[+] {client.user} — farming {name}")
    await push_presence()

@client.event
async def on_resumed():
    # gateway reconnected — re-assert immediately
    await push_presence()
    print("[~] resumed — presence restored")

@client.event
async def on_connect():
    await push_presence()

client.run(TOKEN, bot=False)
