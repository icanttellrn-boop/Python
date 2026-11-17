class BadgeFarmer:
    def __init__(self):
        self.ws                  = None
        self.heartbeat_interval  = None
        self.sequence            = None
        self.session_id          = None
        self.own_id              = None
        self.running             = True

        # независимые таски
        self.time_task           = None
        self.time_start          = None

        self.variety_task        = None
        self.variety_start       = None
        self.game_index          = 0
        self.games_played        = set()
        self.current_game        = None

    # ── payloads ──────────────────────────────────────────────────────────────
    def _presence(self, game=None):
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

    def _identify(self):
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

    # ── time task ─────────────────────────────────────────────────────────────
    async def _task_time(self):
        # если variety уже крутится — не перебиваем её присутствие
        if not self.variety_task or self.variety_task.done():
            self.current_game = TIME_GAME
            await self.ws.send(json.dumps(self._presence(TIME_GAME)))
        print(f"[farm:time] tracking started — {TIME_GAME}")

        ticks = 0
        while True:
            await asyncio.sleep(60)
            ticks += 1
            # отправляем presence только если variety не активна
            if not self.variety_task or self.variety_task.done():
                self.current_game = TIME_GAME
                if ticks % 5 == 0:
                    await self.ws.send(json.dumps(self._presence(TIME_GAME)))

    # ── variety task ──────────────────────────────────────────────────────────
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

        if cmd == "farm":
            if len(parts) < 2:
                await send_msg(channel_id,
                    "```\n"
                    ".farm time      — farm Game Time (runs alongside variety)\n"
                    ".farm variety   — farm Game Variety\n"
                    ".farm stop      — stop everything\n"
                    ".farm stop time — stop only time\n"
                    ".farm stop variety — stop only variety\n"
                    "```")
                return

            sub = parts[1].lower()

            # ── stop ──────────────────────────────────────────────────────────
            if sub == "stop":
                target = parts[2].lower() if len(parts) > 2 else "all"

                if target in ("all", "stop"):
                    if self.time_task and not self.time_task.done():
                        self.time_task.cancel()
                    if self.variety_task and not self.variety_task.done():
                        self.variety_task.cancel()
                    self.time_task     = None
                    self.variety_task  = None
                    self.current_game  = None
                    await self.ws.send(json.dumps(self._presence(None)))
                    await send_msg(channel_id,
                        "🛑 **All farming stopped.** Presence cleared.")

                elif target == "time":
                    if self.time_task and not self.time_task.done():
                        self.time_task.cancel()
                    self.time_task  = None
                    self.time_start = None
                    await send_msg(channel_id,
                        "🛑 **Time farming stopped.** Variety continues.")

                elif target == "variety":
                    if self.variety_task and not self.variety_task.done():
                        self.variety_task.cancel()
                    self.variety_task  = None
                    self.variety_start = None
                    # если time ещё идёт — восстанавливаем его presence
                    if self.time_task and not self.time_task.done():
                        self.current_game = TIME_GAME
                        await self.ws.send(json.dumps(self._presence(TIME_GAME)))
                    else:
                        await self.ws.send(json.dumps(self._presence(None)))
                    await send_msg(channel_id,
                        "🛑 **Variety farming stopped.** Time continues.")
                return

            # ── time ──────────────────────────────────────────────────────────
            if sub == "time":
                if self.time_task and not self.time_task.done():
                    await send_msg(channel_id,
                        "⚠️ Time farming already running.")
                    return
                self.time_start = time.time()
                self.time_task  = asyncio.create_task(self._task_time())
                variety_status  = "running alongside" \
                    if (self.variety_task and not self.variety_task.done()) \
                    else "not active"
                await send_msg(channel_id,
                    f"⚔️ **Game Time farming started.**\n"
                    f"Game: `{TIME_GAME}` | Variety: `{variety_status}`")
                return

            # ── variety ───────────────────────────────────────────────────────
            if sub == "variety":
                if self.variety_task and not self.variety_task.done():
                    await send_msg(channel_id,
                        "⚠️ Variety farming already running.")
                    return
                self.game_index    = 0
                self.games_played.clear()
                self.variety_start = time.time()
                self.variety_task  = asyncio.create_task(self._task_variety())
                time_status = "running" \
                    if (self.time_task and not self.time_task.done()) \
                    else "not active"
                await send_msg(channel_id,
                    f"🎮 **Game Variety farming started.**\n"
                    f"Queue: `{len(GAMES)} games` | "
                    f"Interval: `{ROTATE_INTERVAL}s/game` | "
                    f"Time farming: `{time_status}`")
                return

            await send_msg(channel_id,
                f"❓ Unknown: `{sub}`")

        elif cmd == "status":
            lines = ["**📊 Farm Status**"]

            # time
            if self.time_task and not self.time_task.done():
                e = int(time.time() - self.time_start)
                h, m, s = e//3600, (e%3600)//60, e%60
                lines.append(f"⚔️ Time: `{TIME_GAME}` | `{h:02d}:{m:02d}:{s:02d}`")
            else:
                lines.append("⚔️ Time: `idle`")

            # variety
            if self.variety_task and not self.variety_task.done():
                e = int(time.time() - self.variety_start)
                h, m, s = e//3600, (e%3600)//60, e%60
                prog = self.game_index % len(GAMES)
                lines.append(
                    f"🎮 Variety: `{self.current_game}` | "
                    f"`{prog}/{len(GAMES)}` | "
                    f"Unique: `{len(self.games_played)}` | "
                    f"`{h:02d}:{m:02d}:{s:02d}`"
                )
            else:
                lines.append("🎮 Variety: `idle`")

            await send_msg(channel_id, "\n".join(lines))

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
                        print("\n[!] Reconnect")
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
