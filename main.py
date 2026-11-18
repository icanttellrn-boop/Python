"""
GTA 6 PS5 Rich Presence Selfbot
No third-party discord lib — pure websocket + REST
dep: pip install websocket-client

BEFORE RUNNING:
Paste this URL into any Discord channel and send it — forces cache:
https://cdn.discordapp.com/attachments/1570240024589377689/1572589309666529431/images.jpg
Then run the script.
"""

import json
import os
import sys
import time
import threading
import websocket

TOKEN  = os.environ.get("DISCORD_TOKEN", "")
APP_ID = "1240700149680939090"

# Send this URL in any Discord channel first to force the proxy cache
_CDN   = "cdn.discordapp.com/attachments/1570240024589377689/1572589309666529431/images.jpg"
_LARGE_IMAGE = f"mp:external/{_CDN}"

PRESENCE = {
    "op": 3,
    "d": {
        "since":  None,
        "status": "online",
        "afk":    False,
        "activities": [
            {
                "name":           "Grand Theft Auto VI",
                "type":           0,
                "application_id": APP_ID,
                "details":        "Grand Theft Auto VI",
                "state":          "PlayStation 5",
                "timestamps":     {"start": int(time.time() * 1000)},
                "assets": {
                    "large_image": _LARGE_IMAGE,
                    "large_text":  "Grand Theft Auto VI",
                },
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

    if op == 10:                                      # Hello
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

    elif t == "READY":                                # Identify ACK
        u = msg["d"]["user"]
        print(f"[+] {u['username']}#{u['discriminator']}")
        send(ws, PRESENCE)
        print("[+] presence live — GTA VI / PlayStation 5")

    elif op == 11:                                    # Heartbeat ACK
        pass

    elif op in (7, 9):                                # Reconnect / invalid session
        print(f"[!] op {op} — reconnecting")
        ws.close()


def on_error(ws: websocket.WebSocketApp, error: Exception) -> None:
    print(f"[!] {error}")


def on_close(
    ws: websocket.WebSocketApp,
    code: int | None,
    msg:  str | None,
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
