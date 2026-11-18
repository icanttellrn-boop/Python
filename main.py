"""
GTA 6 PS5 Rich Presence Selfbot — Railway Edition
===================================================
deps: pip install discord.py-self

Railway env vars:
  DISCORD_TOKEN   your user token

Deploy:
  1. Push this file + requirements.txt to a repo
  2. New Railway project → Deploy from GitHub
  3. Set DISCORD_TOKEN in Variables tab
"""

import asyncio
import os
import time

import discord

# ─── CONFIG ───────────────────────────────────────────────────────────────────

TOKEN    = os.environ.get("DISCORD_TOKEN", "PASTE_YOUR_TOKEN_HERE")

APP_ID   = 1240700149680939090   # GTA VI Discord application id (int required)

DETAIL = "Exploring Vice City"
STATE  = "Free Roam"

# ──────────────────────────────────────────────────────────────────────────────


class GTA6Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self._start_time = int(time.time())

    async def setup_hook(self):
        self.loop.create_task(self._set_presence())

    async def on_ready(self):
        print(f"[+] logged in as {self.user} ({self.user.id})")

    async def _set_presence(self):
        await self.wait_until_ready()

        activity = discord.Activity(
            application_id = APP_ID,
            type           = discord.ActivityType.playing,
            name           = "Grand Theft Auto VI",
            details        = DETAIL,
            state          = f"{PLATFORM} • {STATE}",
            timestamps     = {"start": self._start_time},
            assets         = {
                "large_image": "gta6",
                "large_text":  "Grand Theft Auto VI",
                "small_image": "ps5_controller",
                "small_text":  PLATFORM,
            },
        )

        await self.change_presence(
            status   = discord.Status.online,
            activity = activity,
        )

        print(f"[+] presence locked → {DETAIL} | {STATE}")


PLATFORM = "PlayStation 5"


if __name__ == "__main__":
    if TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print("[!] Set the DISCORD_TOKEN environment variable.")
    else:
        bot = GTA6Bot()
        bot.run(TOKEN, bot=False)   # bot=False = user token / selfbot
