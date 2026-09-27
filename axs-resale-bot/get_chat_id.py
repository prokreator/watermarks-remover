"""Print the chat id of whoever last messaged your bot.

1. Put TELEGRAM_BOT_TOKEN in .env
2. Open your bot in Telegram and send it any message (e.g. "hi")
3. Run: python get_chat_id.py
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", encoding="utf-8-sig")
token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    sys.exit("Set TELEGRAM_BOT_TOKEN in .env first.")

updates = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20).json()
if not updates.get("ok"):
    sys.exit(f"Telegram said: {updates}")
chats = {
    u["message"]["chat"]["id"]: u["message"]["chat"].get("first_name", "")
    for u in updates["result"]
    if "message" in u
}
if not chats:
    sys.exit("No messages yet. Send your bot a message in Telegram, then rerun.")
for chat_id, name in chats.items():
    print(f"TELEGRAM_CHAT_ID={chat_id}   ({name})")
