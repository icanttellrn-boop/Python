"""
GTA 6 PS5 Rich Presence Selfbot
dep: pip install websocket-client
"""

import json
import os
import sys
import time
import threading
import websocket

TOKEN  = os.environ.get("DISCORD_TOKEN", "")
APP_ID = "1572591435482529822"

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
                    "large_image": "gta6",
                    "large_text":  "Grand Theft Auto VI",
                },
            }
        ],
    },
}

GATEWAY = "wss://gateway.discord.gg/?v=10&encoding=json"

heartbeat_interval: float | None = None
sequence:           int   | None = None


def send(ws, payload):
    ws.send(json.dumps(payload))


def heartbeat_loop(ws):
    while True:
        time.sleep(heartbeat_interval / 1000)
        send(ws, {"op": 1, "d": sequence})


def on_open(ws):
    print("[+] connected")


def on_message(ws, raw):
    global heartbeat_interval, sequence

    msg = json.loads(raw)
    op  = msg.get("op")
    t   = msg.get("t")

    if msg.get("s") is not None:
        sequence = msg["s"]

    if op == 10:
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

    elif t == "READY":
        u = msg["d"]["user"]
        print(f"[+] {u['username']}#{u['discriminator']}")
        send(ws, PRESENCE)
        print("[+] presence live — GTA VI / PlayStation 5")

    elif op == 11:
        pass

    elif op in (7, 9):
        print(f"[!] op {op} — reconnecting")
        ws.close()


def on_error(ws, error):
    print(f"[!] {error}")


def on_close(ws, code, msg):
    print(f"[!] closed ({code}) — retry in 5 s")
    time.sleep(5)
    connect()


def connect():
    websocket.WebSocketApp(
        "wss://gateway.discord.gg/?v=10&encoding=json",
        on_open    = on_open,
        on_message = on_message,
        on_error   = on_error,
        on_close   = on_close,
    ).run_forever()


if __name__ == "__main__":
    if not TOKEN:
        print("[!] DISCORD_TOKEN not set")
        sys.exit(1)
    connect()
