import json, os, subprocess

cfg = {
    "BOT_TOKEN": os.environ["BOT_TOKEN"],
    "chat_id": int(os.environ["CHAT_ID"]),
    "group": os.environ["GROUP"],
}
with open("config.json", "w") as f:
    json.dump(cfg, f)

subprocess.run(["python3", "send_poll.py"], check=True)
