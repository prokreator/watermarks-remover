"""Check the Telegram setup step by step and say exactly what is wrong.

Run: python test_telegram.py   (Windows: double-click test_telegram.bat)
It sends one test message to your phone if everything is correct.
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def fail(msg: str, fix: str) -> None:
    print(f"  [FAIL] {msg}\n         FIX: {fix}\n")
    sys.exit(1)


def main() -> None:
    print("\nTelegram setup check\n")

    env = HERE / ".env"
    if not env.exists():
        if (HERE / ".env.txt").exists():
            fail(
                "Found .env.txt instead of .env (Windows added .txt).",
                "Rename it: in this folder run  ren .env.txt .env",
            )
        fail(".env file not found.", "Copy .env.example to .env and fill it in.")
    ok(".env found")
    load_dotenv(env, encoding="utf-8-sig", override=True)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or token.startswith("123456789:AAxx"):
        fail(
            "TELEGRAM_BOT_TOKEN is empty or still the example.", "Paste the token from @BotFather."
        )
    if ":" not in token or " " in token:
        fail(
            "TELEGRAM_BOT_TOKEN doesn't look like a token.",
            "It should look like 123456789:AA... with no spaces or quotes.",
        )

    try:
        http = httpx.Client(timeout=20)
        me = http.get(f"https://api.telegram.org/bot{token}/getMe").json()
    except httpx.HTTPError as e:
        fail(
            f"Can't reach api.telegram.org ({e.__class__.__name__}).",
            "The RDP has no internet or a firewall/proxy blocks Telegram. "
            "Open https://api.telegram.org in the RDP's browser to check.",
        )
    if not me.get("ok"):
        fail(
            f"Telegram rejected the token: {me.get('description')}",
            "Copy the token again from @BotFather (/mybots > your bot > API Token).",
        )
    bot = me["result"]
    ok(f"Token valid: bot is @{bot['username']}")

    if not chat_id:
        fail("TELEGRAM_CHAT_ID is empty.", "Run get_chat_id.bat and paste the line into .env.")
    if not chat_id.lstrip("-").isdigit():
        fail(f"TELEGRAM_CHAT_ID '{chat_id}' is not a number.", "Run get_chat_id.bat.")
    if chat_id == str(bot["id"]):
        fail(
            "TELEGRAM_CHAT_ID is the BOT's id (the number at the start of the token), not yours.",
            f"Message @{bot['username']} from your phone, run get_chat_id.bat, use that number.",
        )
    ok(f"Chat id looks right: {chat_id}")

    hook = http.get(f"https://api.telegram.org/bot{token}/getWebhookInfo").json()
    if hook.get("result", {}).get("url"):
        http.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
        ok("Removed an old webhook that would have stopped the buttons working")

    r = http.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "🔔 Test notification from your AXS resale bot. If your phone buzzed, you're set.",
        },
    ).json()
    if not r.get("ok"):
        desc = (r.get("description") or "").lower()
        if "chat not found" in desc:
            fix = (
                f"On your phone open @{bot['username']}, press START, send 'hi', "
                "then run get_chat_id.bat again and update TELEGRAM_CHAT_ID."
            )
        elif "blocked" in desc:
            fix = f"You blocked the bot. Open @{bot['username']} and tap Unblock / Restart."
        else:
            fix = "See the error above."
        fail(f"Telegram couldn't message you: {r.get('description')}", fix)
    ok("Test message sent")

    print(
        "\nCheck your phone now.\n"
        "  - Message arrived AND phone buzzed: Telegram is working.\n"
        "  - Message is in the chat but NO buzz/banner: it's your phone settings:\n"
        "      * In Telegram open the bot chat > tap its name > make sure it's not Muted\n"
        "      * Telegram > Settings > Notifications > Private chats: ON\n"
        "      * Phone Settings > Apps/Notifications > Telegram: allowed\n"
        "      * Turn off Do Not Disturb / Focus (or allow Telegram through it)\n"
        "      * Android: Battery > Telegram > Unrestricted\n"
        "      * Log out of Telegram Desktop/Web if it's open (it takes the notifications)\n"
    )


if __name__ == "__main__":
    main()
