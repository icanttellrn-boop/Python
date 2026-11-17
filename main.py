# language: Python 3.11+, file: badge_farmer.py
# pip install websockets aiohttp
# Commands: .farm time | .farm variety | .farm stop | .status

import asyncio, json, time, signal, sys, os
import aiohttp, websockets

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN            = os.environ.get("TOKEN", "")
PREFIX           = "."
TIME_GAME        = "Minecraft"
ROTATE_INTERVAL  = 65
STATUS           = "online"
# ──────────────────────────────────────────────────────────────────────────────

GATEWAY  = "wss://gateway.discord.gg/?v=10&encoding=json"
API_BASE = "https://discord.com/api/v10"

GAMES = [
    "League of Legends","Valorant","Minecraft","Fortnite","Apex Legends",
    "Counter-Strike 2","Dota 2","World of Warcraft","Overwatch 2","Rocket League",
    "Grand Theft Auto V","Rainbow Six Siege","Destiny 2","Path of Exile",
    "Dead by Daylight","Among Us","Fall Guys","Rust","ARK: Survival Evolved",
    "7 Days to Die","The Forest","Subnautica","Terraria","Stardew Valley",
    "RimWorld","Cities: Skylines","Euro Truck Simulator 2","American Truck Simulator",
    "Farming Simulator 22","Football Manager 2024","Cyberpunk 2077",
    "Red Dead Redemption 2","Elden Ring","Dark Souls III","Sekiro: Shadows Die Twice",
    "Monster Hunter: World","Monster Hunter Rise","Devil May Cry 5",
    "Resident Evil Village","Resident Evil 4","Halo Infinite","Doom Eternal",
    "Quake Champions","Team Fortress 2","Payday 2","Left 4 Dead 2","Back 4 Blood",
    "Dying Light 2","Deep Rock Galactic","Helldivers 2","Risk of Rain 2",
    "Gunfire Reborn","Borderlands 3","The Elder Scrolls Online","Guild Wars 2",
    "Final Fantasy XIV","Black Desert Online","Lost Ark","New World","Warframe",
    "Dauntless","Brawlhalla","Smite","Paladins","PUBG: BATTLEGROUNDS",
    "Call of Duty: Warzone","Escape from Tarkov","Hunt: Showdown","DayZ",
    "The Witcher 3: Wild Hunt","Gears 5","Naraka: Bladepoint","Super People",
    "Albion Online","EVE Online","Elite Dangerous","No Man's Sky","Deathloop",
    "Sifu","Ghostrunner","Control","Alan Wake 2","Hi-Fi Rush","Lies of P",
    "Armored Core VI","Street Fighter 6","Tekken 8","Mortal Kombat 11",
    "Dragon Ball FighterZ","Guilty Gear Strive","BlazBlue: Cross Tag Battle",
    "NBA 2K24","FIFA 23","WWE 2K23","Planet Coaster","Satisfactory",
    "Factorio","Dyson Sphere Program","Icarus","Valheim","V Rising",
    "Green Hell","The Long Dark","Subnautica: Below Zero","Grounded",
    "Core Keeper","Coral Island","Palia","Wayfinder","Throne and Liberty",
]

# ─── REST ─────────────────────────────────────────────────────────────────────
async def api(method: str, path: str, body: dict = None):
    headers = {"Authorization": TOKEN, "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as s:
        r = await s.request(method, f"{API_BASE}{path}",
                            headers=headers,
                            json=body if body else None)
        return r

async def send_msg(channel_id: str, content: str):
    await api("POST", f"/channels/{channel_id}/messages", {"content": content})

async def del_msg(channel_id: str, message_id: str):
    await api("DELETE", f"/channels/{channel_id}/messages/{message_id}")

# ─── FARMER ───────────────────────────────────────────────────────────────────
class BadgeFarmer:
    def __init__(self):
        self.ws                  = None
        self.heartbeat_interval  = None
        self.sequence            = None
        self.session_id          = None
        self.own_id              = None
        self.running             = True

        self.farm_task           = None
        self.farm_mode           = None
        self.farm_start          = None
        self.game_index          = 0
        self.games_played        = set()
        self.current_game        = None

    # ── payloads ──────────────────────────────────────────────────────────────
    def _presence(self, game: str | None = None) -> dict:
        activities = []
        if game:
            activities = [{
                "name": game, "type": 0,
                "timestamps": {"start": int(time.time() * 1000)}
            }]
        return {"op": 3, "d": {
            "since": None, "activities": activities,
            "status": STATUS, "afk": False
        }}

    def _identify(self) -> dict:
        return {
            "op": 2,
            "d": {
                "token": TOKEN,
                "capabilities": 16381,
                "properties": {
                    "os": "Windows", "browser": "Discord Client", "device": "",
                    "system_locale": "en-US",
                    "browser_user_agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "browser_version": "120.0.0.0",
                    "os_version": "10",
                    "release_channel": "stable",
                    "client_build_number": 999999,
                    "client_event_source": None,
                },
                "presence": {"status": STATUS, "since": 0,
                             "activities": [], "afk": False},
                "compress": False,
                "client_state": {
                    "guild_versions": {}, "highest_last_message_id": "0",
                    "read_state_version": 0, "user_guild_settings_version": -1,
                    "user_settings_version": -1, "private_channels_version": "0",
                    "api_code_version": 0,
                },
            },
        }

    # ── heartbeat ─────────────────────────────────────────────────────────────
    async def _heartbeat_loop(self):
        while self.running:
            await asyncio.sleep(self.heartbeat_interval / 1000)
            await self.ws.send(json.dumps({"op": 1, "d": self.sequence}))

    # ── farm tasks ────────────────────────────────────────────────────────────
    async def _task_time(self):
        self.current_game = TIME_GAME
        await self.ws.send(json.dumps(self._presence(TIME_GAME)))
        print(f"[farm:time] {TIME_GAME}")
        ticks = 0
        while True:
            await asyncio.sleep(60)
            ticks += 1
            if ticks % 5 == 0:
                await self.ws.send(json.dumps(self._presence(TIME_GAME)))

    async def _task_variety(self):
        print(f"[farm:variety] {len(GAMES)} games queued")
        while True:
            game = GAMES[self.game_index % len(GAMES)]
            self.current_game = game
            self.games_played.add(game)
            await self.ws.send(json.dumps(self._presence(game)))
            print(f"[variety] [{self.game_index + 1}/{len(GAMES)}] {game}")
            self.game_index += 1
            if self.game_index >= len(GAMES):
                print(f"[variety] full cycle — {len(self.games_played)} unique")
                self.game_index = 0
            await asyncio.sleep(ROTATE_INTERVAL)

    def _stop_farm(self):
        if self.farm_task and not self.farm_task.done():
            self.farm_task.cancel()
        self.farm_task    = None
        self.farm_mode    = None
        self.current_game = None

    # ── commands ──────────────────────────────────────────────────────────────
    async def _handle(self, d: dict):
        content    = (d.get("content") or "").strip()
        channel_id = d["channel_id"]
        message_id = d["id"]

        if not content.startswith(PREFIX):
            return

        asyncio.create_task(del_msg(channel_id, message_id))

        parts = content[len(PREFIX):].split()
        if not parts:
            return
        cmd = parts[0].lower()

        # ── .farm ─────────────────────────────────────────────────────────────
        if cmd == "farm":
            if len(parts) < 2:
                await send_msg(channel_id,
                    "```\n.farm time\n.farm variety\n.farm stop\n```")
                return

            sub = parts[1].lower()

            if sub == "stop":
                self._stop_farm()
                await self.ws.send(json.dumps(self._presence(None)))
                await send_msg(channel_id,
                    "🛑 **Farming stopped.** Presence cleared.")

            elif sub == "time":
                self._stop_farm()
                self.farm_mode  = "time"
                self.farm_start = time.time()
                self.farm_task  = asyncio.create_task(self._task_time())
                await send_msg(channel_id,
                    f"⚔️ **Game Time farming started.**\n"
                    f"Game: `{TIME_GAME}` | Status: `{STATUS}`")

            elif sub == "variety":
                self._stop_farm()
                self.game_index  = 0
                self.games_played.clear()
                self.farm_mode   = "variety"
                self.farm_start  = time.time()
                self.farm_task   = asyncio.create_task(self._task_variety())
                await send_msg(channel_id,
                    f"🎮 **Game Variety farming started.**\n"
                    f"Queue: `{len(GAMES)} games` | "
                    f"Interval: `{ROTATE_INTERVAL}s/game`")

            else:
                await send_msg(channel_id,
                    f"❓ Unknown: `{sub}`. Use `time`, `variety`, `stop`.")

        # ── .status ───────────────────────────────────────────────────────────
        elif cmd == "status":
            if not self.farm_mode:
                await send_msg(channel_id, "💤 **Idle.** Nothing running.")
                return

            elapsed = int(time.time() - self.farm_start)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60

            if self.farm_mode == "time":
                await send_msg(channel_id,
                    f"**📊 Farm Status**\n"
                    f"Mode: `TIME`\n"
                    f"Game: `{self.current_game}`\n"
                    f"Uptime: `{h:02d}:{m:02d}:{s:02d}`")

            elif self.farm_mode == "variety":
                await send_msg(channel_id,
                    f"**📊 Farm Status**\n"
                    f"Mode: `VARIETY`\n"
                    f"Current: `{self.current_game}`\n"
                    f"Progress: `{self.game_index % len(GAMES)}/{len(GAMES)}`\n"
                    f"Unique sent: `{len(self.games_played)}`\n"
                    f"Uptime: `{h:02d}:{m:02d}:{s:02d}`")

    # ── gateway loop ──────────────────────────────────────────────────────────
    async def run(self):
        print("[*] Connecting...")
        async with websockets.connect(
            GATEWAY,
            extra_headers={"User-Agent": "Mozilla/5.0"},
            max_size=10_000_000
        ) as self.ws:

            msg = json.loads(await self.ws.recv())
            assert msg["op"] == 10
            self.heartbeat_interval = msg["d"]["heartbeat_interval"]

            await self.ws.send(json.dumps(self._identify()))
            asyncio.create_task(self._heartbeat_loop())

            msg = json.loads(await self.ws.recv())
            if msg.get("t") == "READY":
                user = msg["d"]["user"]
                self.own_id     = user["id"]
                self.session_id = msg["d"]["session_id"]
                tag = f"{user['username']}#{user.get('discriminator','0')}"
                print(f"[+] Logged in: {tag}")
                print(f"[*] Prefix: {PREFIX} | Commands: farm, status")
            else:
                print(f"[!] Unexpected: {msg}")
                return

            try:
                async for raw in self.ws:
                    msg = json.loads(raw)
                    if msg.get("s"):
                        self.sequence = msg["s"]

                    op = msg["op"]
                    if op == 7:
                        print("\n[!] Reconnect requested")
                        break
                    if op == 9:
                        print("\n[!] Invalid session")
                        await asyncio.sleep(5)
                        break
                    if op != 0:
                        continue

                    if msg.get("t") == "MESSAGE_CREATE":
                        d = msg.get("d", {})
                        if d.get("author", {}).get("id") == self.own_id:
                            asyncio.create_task(self._handle(d))

            except websockets.ConnectionClosed as e:
                print(f"\n[!] Closed: {e}")

# ─── ENTRY ────────────────────────────────────────────────────────────────────
async def main():
    if not TOKEN:
        print("[!] TOKEN not set. Add it as environment variable.")
        sys.exit(1)

    farmer = BadgeFarmer()

    def _stop(*_):
        print("\n[*] Stopping...")
        farmer.running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    while True:
        try:
            await farmer.run()
        except Exception as e:
            print(f"[!] Error: {e} — reconnect in 10s")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
