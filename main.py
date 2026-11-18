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
import urllib.request
import urllib.error

TOKEN   = os.environ.get("DISCORD_TOKEN", "")
APP_ID  = "1240700149680939090"

PRESENCE = {
    "op": 3,
    "d": {
        "since": None,
        "activities": [
            {
                "name":             "Grand Theft Auto VI",
                "type":             0,
                "application_id":   APP_ID,
                "details":          "Exploring Vice City",
                "state":            "PlayStation 5 - Free Roam",
                "timestamps":       {"start": int(time.time() * 1000)},
                "assets": {
                    "large_image":  APP_ID + "/gta6",
                    "large_text":   "Grand Theft Auto VI",
                    "small_image":  APP_ID + "/ps5_controller",
                    "small_text":   "PlayStation 5",
                },
            }
        ],
        "status": "online",
        "afk":    False,
    }
}

GATEWAY = "wss://gateway.discord.gg/?v=10&encoding=json"

heartbeat_interval = None
sequence           = None
ws_app             = None


def send(ws, payload):
    ws.send(json.dumps(payload))


def heartbeat_loop(ws):
    while True:
        time.sleep(heartbeat_interval / 1000)
        send(ws, {"op": 1, "d": sequence})


def on_open(ws):
    print("[+] connected to gateway")


def on_message(ws, raw):
    global heartbeat_interval, sequence

    msg = json.loads(raw)
    op  = msg.get("op")
    t   = msg.get("t")

    if msg.get("s"):
        sequence = msg["s"]

    # Hello — start heartbeat + identify
    if op == 10:
        heartbeat_interval = msg["d"]["heartbeat_interval"]
        threading.Thread(target=heartbeat_loop, args=(ws,), daemon=True).start()

        # Identify as user (selfbot)
        send(ws, {
            "op": 2,
            "d": {
                "token":      TOKEN,
                "intents":    0,
                "properties": {
                    "os":      "Windows",
                    "browser": "Discord Client",
                    "device":  "Discord Client",
                },
                "presence": PRESENCE["d"],
            }
        })

    # Ready — set presence
    elif t == "READY":
        user = msg["d"]["user"]
        print(f"[+] logged in as {user['username']}#{user['discriminator']}")
        send(ws, PRESENCE)
        print("[+] presence set — GTA VI / PlayStation 5")

    # Heartbeat ACK
    elif op == 11:
        pass

    # Reconnect / Invalid session
    elif op in (7, 9):
        print(f"[!] op {op} — reconnecting")
        ws.close()


def on_error(ws, error):
    print(f"[!] error: {error}")


def on_close(ws, code, msg):
    print(f"[!] closed ({code}) — reconnecting in 5s")
    time.sleep(5)
    connect()


def connect():
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
        print("[!] Set DISCORD_TOKEN env var")
        sys.exit(1)
    connect()
