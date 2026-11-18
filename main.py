"""
GTA 6 PS5 Rich Presence Selfbot
No third-party discord lib — pure websocket + REST
dep: pip install websocket-client
"""

import json
import os
import sys
import time
import threading
import websocket

TOKEN  = os.environ.get("DISCORD_TOKEN", "")
APP_ID = "1240700149680939090"

# Discord external image proxy — wraps any public URL.
# Format: external/<hash>/<encoded-url>
# Hash is arbitrary for selfbot presence; Discord accepts the bare path.
_LOGO_URL = (
    "mp:external/gta6-logo"
    "/https/i.imgur.com/43bdw9g.png"
)

PRESENCE = {
    "op": 3,
    "d": {
        "since":  None,
        "status": "online",
        "afk":    False,
        "activities": [
            {
                "name":       "Grand Theft Auto VI",
                "type":       1,                          # Streaming
                "url":        "https://www.twitch.tv/playstation",
                "details":    "Grand Theft Auto VI",
                "state":      "PlayStation 5",
                "timestamps": {"start": int(time.time() * 1000)},
                "assets": {
                    "large_image": _LOGO_URL,
                    "large_text":  "Grand Theft Auto VI",
                },
                "application_id": APP_ID,
            }
        ],
    },
}

GATEWAY = "wss://gateway.discord.gg/?v=10&encoding=json"

heartbeat_interval: float | None = None
sequence:           int   | None = None
ws_app:             websocket.WebSocketApp | None = None


def send(ws: websocket.WebSocketApp, payload: dict) -> None:
    ws.send(json.dumps(payload))


def heartbeat_loop(ws: websocket.WebSocketApp) -> None:
    while True:
        time.sleep(heartbeat_interval / 1000)
        send(ws, {"op": 1, "d": sequence})


def on_open(ws: websocket.WebSocketApp) -> None:
    print("[+] connected")


def on_message(ws: websocket.WebSocketApp, raw: str) -> None:
    global heartbeat_interval, sequence

    msg = json.loads(raw)
    op  = msg.get("op")
    t   = msg.get("t")

    if msg.get("s") is not None:
        sequence = msg["s"]

    if op == 10:                                          # Hello
        heartbeat_interval = msg["d"]["heartbeat_interval"]
        threading.Thread(
            target=heartbeat_loop, args=(ws,), daemon=True
        ).start()

        send(ws, {
            "op": 2,
            "d": {
                "token":   TOKEN,
                "intents": 0,
                "properties": {
                    "os":      "Windows",
                    "browser": "Discord Client",
                    "device":  "Discord Client",
                },
                "presence": PRESENCE["d"],
            },
        })

    elif t == "READY":                                    # Identify ACK
        u = msg["d"]["user"]
        print(f"[+] {u['username']}#{u['discriminator']}")
        send(ws, PRESENCE)
        print("[+] presence live — GTA VI / PlayStation 5")

    elif op == 11:                                        # Heartbeat ACK
        pass

    elif op in (7, 9):                                    # Reconnect / invalid session
        print(f"[!] op {op} — reconnecting")
        ws.close()


def on_error(ws: websocket.WebSocketApp, error: Exception) -> None:
    print(f"[!] {error}")


def on_close(
    ws: websocket.WebSocketApp,
    code: int | None,
    msg: str | None,
) -> None:
    print(f"[!] closed ({code}) — retry in 5 s")
    time.sleep(5)
    connect()


def connect() -> None:
    global ws_app
    ws_app = websocket.WebSocketApp(
        GATEWAY,
        on_open    = on_open,
        on_message = on_message,
        on_error   = on_error,
        on_close   = on_close,
    )
    ws_app.run_forever()


if __name__ == "__main__":
    if not TOKEN:
        print("[!] DISCORD_TOKEN not set")
        sys.exit(1)
    connect()
