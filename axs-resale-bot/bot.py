"""AXS UK resale watcher with Telegram alerts.

Loads an AXS event page in a real (Playwright) Chromium browser every
CHECK_INTERVAL seconds, looks for resale listings matching your keywords
(e.g. "standing"), and pings you on Telegram with a screenshot and a link
the moment one shows up, so you can check out on your phone.

It does NOT auto-purchase: AXS checkout sits behind a queue, captcha and a
logged-in payment step, and automating that breaks the AXS terms of use.
Speed comes from the alert; the buying is done by you.

Telegram commands (only accepted from TELEGRAM_CHAT_ID; also on the button keyboard):
    /status  - current state and last check time
    /check   - run a check right now
    /pause   - stop checking
    /resume  - start checking again
    /shot    - send a screenshot of the page as the bot currently sees it
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from dotenv import load_dotenv

log = logging.getLogger("axs-resale-bot")

HERE = Path(__file__).resolve().parent

DEFAULT_BLOCKED = (
    "access denied,you are now in line,queue-it,verify you are human,"
    "are you a robot,pardon our interruption,request unsuccessful"
)


def _csv(value: str) -> list[str]:
    return [p.strip().lower() for p in value.split(",") if p.strip()]


@dataclass
class Config:
    token: str
    chat_id: str
    event_url: str
    event_name: str
    match_keywords: list[str]
    blocked_phrases: list[str]
    max_price: float | None
    interval: int
    jitter: int
    headless: bool
    profile_dir: Path

    @classmethod
    def from_env(cls) -> Config:
        load_dotenv(HERE / ".env", encoding="utf-8-sig")
        missing = [
            k
            for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "AXS_EVENT_URL")
            if not os.getenv(k)
        ]
        if missing:
            sys.exit(f"Missing required settings in .env: {', '.join(missing)}")
        max_price = os.getenv("MAX_PRICE", "").strip()
        return cls(
            token=os.environ["TELEGRAM_BOT_TOKEN"],
            chat_id=os.environ["TELEGRAM_CHAT_ID"].strip(),
            event_url=os.environ["AXS_EVENT_URL"].strip(),
            event_name=os.getenv("EVENT_NAME", "").strip() or "your AXS event",
            match_keywords=_csv(os.getenv("MATCH_KEYWORDS", "standing,general admission")),
            blocked_phrases=_csv(os.getenv("BLOCKED_PHRASES", DEFAULT_BLOCKED)),
            max_price=float(max_price) if max_price else None,
            # Floor at 30s: hammering AXS gets you rate-limited or blocked.
            interval=max(30, int(os.getenv("CHECK_INTERVAL", "60"))),
            jitter=max(0, int(os.getenv("CHECK_JITTER", "20"))),
            headless=os.getenv("HEADLESS", "true").lower() != "false",
            profile_dir=Path(os.getenv("PROFILE_DIR", str(HERE / "browser-profile"))),
        )


# ---------------------------------------------------------------- detection

PRICE_RE = re.compile(r"£\s?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)")


@dataclass
class Result:
    status: str  # "available" | "none" | "blocked"
    matches: list[str] = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256("\n".join(sorted(self.matches)).encode()).hexdigest()[:16]


def prices_in(line: str) -> list[float]:
    return [float(p.replace(",", "")) for p in PRICE_RE.findall(line)]


def analyse(text: str, cfg: Config) -> Result:
    """Decide from the page's visible text whether matching tickets are listed.

    A line counts as a match when it contains one of MATCH_KEYWORDS and a £
    price (at or under MAX_PRICE if set). Keyword-only lines such as a
    "Standing" section heading with nothing for sale don't count.
    """
    lower = text.lower()
    if any(p in lower for p in cfg.blocked_phrases):
        return Result("blocked")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    matches: list[str] = []
    for i, line in enumerate(lines):
        if not any(k in line.lower() for k in cfg.match_keywords):
            continue
        # The price is often on the next line or two of the listing card.
        window = " | ".join(lines[i : i + 3])
        prices = prices_in(window)
        if not prices:
            continue
        if cfg.max_price is not None and min(prices) > cfg.max_price:
            continue
        matches.append(window[:200])

    if matches:
        return Result("available", matches)
    return Result("none")


# ---------------------------------------------------------------- telegram


# Buttons shown under the chat box; tapping one sends its text to the bot.
BUTTONS = {
    "📊 Status": "/status",
    "🔍 Check now": "/check",
    "📸 Screenshot": "/shot",
    "⏸ Pause": "/pause",
    "▶️ Resume": "/resume",
}
KEYBOARD = {
    "keyboard": [
        [{"text": "📊 Status"}, {"text": "🔍 Check now"}],
        [{"text": "📸 Screenshot"}, {"text": "⏸ Pause"}, {"text": "▶️ Resume"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}
MENU_COMMANDS = [
    {"command": "status", "description": "Watching or paused, last check"},
    {"command": "check", "description": "Check for tickets right now"},
    {"command": "shot", "description": "Screenshot of the page"},
    {"command": "pause", "description": "Stop checking"},
    {"command": "resume", "description": "Start checking again"},
    {"command": "help", "description": "Show commands and buttons"},
]


def buy_button(url: str) -> dict:
    return {"inline_keyboard": [[{"text": "🎟️ BUY NOW ON AXS", "url": url}]]}


class Telegram:
    def __init__(self, token: str, chat_id: str) -> None:
        self.chat_id = chat_id
        self.base = f"https://api.telegram.org/bot{token}"
        self.http = httpx.AsyncClient(timeout=40)
        self.offset = 0

    async def send(self, text: str, markup: dict | None = None) -> bool:
        body = {"chat_id": self.chat_id, "text": text, "disable_web_page_preview": True}
        if markup:
            body["reply_markup"] = markup
        try:
            r = await self.http.post(f"{self.base}/sendMessage", json=body)
            ok = r.json().get("ok", False)
            if not ok:
                log.warning("Telegram refused message: %s", r.text)
            return ok
        except (httpx.HTTPError, ValueError) as e:
            log.warning("Telegram send failed: %s", e)
            return False

    async def set_menu(self) -> None:
        """Fill the Telegram "Menu" button with our commands (same as BotFather /setcommands)."""
        try:
            await self.http.post(f"{self.base}/setMyCommands", json={"commands": MENU_COMMANDS})
        except httpx.HTTPError as e:
            log.warning("Telegram setMyCommands failed: %s", e)

    async def photo(self, png: bytes, caption: str = "") -> None:
        try:
            await self.http.post(
                f"{self.base}/sendPhoto",
                data={"chat_id": self.chat_id, "caption": caption[:1000]},
                files={"photo": ("page.png", png, "image/png")},
            )
        except httpx.HTTPError as e:
            log.warning("Telegram photo failed: %s", e)

    async def commands(self) -> list[str]:
        """Long-poll for new messages; return commands sent from our chat only."""
        try:
            r = await self.http.get(
                f"{self.base}/getUpdates", params={"offset": self.offset, "timeout": 30}
            )
            updates = r.json().get("result", [])
        except (httpx.HTTPError, ValueError) as e:
            log.warning("Telegram poll failed: %s", e)
            await asyncio.sleep(5)
            return []
        out = []
        for u in updates:
            self.offset = u["update_id"] + 1
            msg = u.get("message") or {}
            if str(msg.get("chat", {}).get("id")) != self.chat_id:
                continue  # ignore strangers who find the bot
            text = (msg.get("text") or "").strip()
            if text in BUTTONS:
                out.append(BUTTONS[text])
            elif text.startswith("/"):
                out.append(text.split()[0].split("@")[0].lower())
        return out


# ---------------------------------------------------------------- watcher


class Watcher:
    def __init__(self, cfg: Config, tg: Telegram) -> None:
        self.cfg = cfg
        self.tg = tg
        self.paused = False
        self.last_check: float | None = None
        self.last_status = "not checked yet"
        self.last_alert_fp: str | None = None
        self.blocked_alerted = False
        self.consecutive_errors = 0
        self.checks = 0
        self.wake = asyncio.Event()
        self.lock = asyncio.Lock()
        self.page = None

    async def start_browser(self, pw) -> None:
        self.cfg.profile_dir.mkdir(parents=True, exist_ok=True)
        ctx = await pw.chromium.launch_persistent_context(
            str(self.cfg.profile_dir),
            headless=self.cfg.headless,
            locale="en-GB",
            timezone_id="Europe/London",
            viewport={"width": 1280, "height": 1800},
        )
        self.page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    async def load(self) -> str:
        await self.page.goto(self.cfg.event_url, wait_until="domcontentloaded", timeout=60_000)
        # AXS keeps long-lived connections open, so "networkidle" may never come.
        with contextlib.suppress(Exception):
            await self.page.wait_for_load_state("networkidle", timeout=20_000)
        await self.page.wait_for_timeout(2_000)
        return await self.page.inner_text("body")

    async def check(self, manual: bool = False) -> None:
        async with self.lock:
            self.checks += 1
            try:
                text = await self.load()
            except Exception as e:
                self.consecutive_errors += 1
                self.last_status = f"error: {e.__class__.__name__}"
                log.warning("Check failed: %s", e)
                if self.consecutive_errors == 5:
                    await self.tg.send(f"⚠️ 5 checks in a row failed (latest: {e}). Still trying.")
                return
            self.consecutive_errors = 0
            self.last_check = time.time()
            result = analyse(text, self.cfg)
            self.last_status = result.status
            log.info("Check #%d: %s %s", self.checks, result.status, result.matches[:3])

            if result.status == "blocked":
                if not self.blocked_alerted or manual:
                    self.blocked_alerted = True
                    await self.tg.photo(
                        await self.page.screenshot(),
                        "🚧 AXS is showing a queue / bot check. I'll keep retrying. "
                        "If it persists, raise CHECK_INTERVAL or run once with "
                        "HEADLESS=false and solve it by hand.",
                    )
                return
            self.blocked_alerted = False

            if result.status == "available":
                if result.fingerprint != self.last_alert_fp or manual:
                    self.last_alert_fp = result.fingerprint
                    lines = "\n".join(f"• {m}" for m in result.matches[:8])
                    await self.tg.send(
                        f"🎟️ RESALE TICKETS FOUND!\n{self.cfg.event_name}\n\n{lines}\n\n"
                        f"👉 {self.cfg.event_url}",
                        buy_button(self.cfg.event_url),
                    )
                    await self.tg.photo(await self.page.screenshot(full_page=True))
                    # A second nudge so your phone buzzes twice.
                    await self.tg.send("⏰ Go go go!")
            else:
                if self.last_alert_fp:
                    await self.tg.send("Listings gone (probably bought). Watching again.")
                self.last_alert_fp = None
                if manual:
                    await self.tg.send("Checked: nothing matching right now.")

    async def loop(self) -> None:
        while True:
            if not self.paused:
                await self.check()
            delay = self.cfg.interval + random.uniform(0, self.cfg.jitter)  # noqa: S311
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.wake.wait(), timeout=delay)
            self.wake.clear()

    async def handle_commands(self) -> None:
        while True:
            for cmd in await self.tg.commands():
                if cmd in ("/start", "/help"):
                    await self.tg.send(
                        "Tap the buttons below, or use the Menu button.\n\n"
                        + __doc__.split("Telegram commands")[1].split(":", 1)[1].strip(),
                        KEYBOARD,
                    )
                elif cmd == "/status":
                    ago = (
                        f"{int(time.time() - self.last_check)}s ago" if self.last_check else "never"
                    )
                    await self.tg.send(
                        f"{'⏸ Paused' if self.paused else '▶️ Watching'}: {self.cfg.event_name}\n"
                        f"Last check: {ago} ({self.last_status})\n"
                        f"Checks run: {self.checks}\n"
                        f"Keywords: {', '.join(self.cfg.match_keywords)}\n"
                        f"Max price: {self.cfg.max_price or 'any'}\n"
                        f"Every ~{self.cfg.interval}s\n{self.cfg.event_url}",
                        buy_button(self.cfg.event_url),
                    )
                elif cmd == "/check":
                    await self.tg.send("Checking…")
                    await self.check(manual=True)
                elif cmd == "/pause":
                    self.paused = True
                    await self.tg.send("⏸ Paused. /resume to continue.")
                elif cmd == "/resume":
                    self.paused = False
                    self.wake.set()
                    await self.tg.send("▶️ Resumed.")
                elif cmd == "/shot":
                    async with self.lock:
                        await self.tg.photo(await self.page.screenshot(), self.page.url)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = Config.from_env()
    tg = Telegram(cfg.token, cfg.chat_id)

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        w = Watcher(cfg, tg)
        await w.start_browser(pw)
        await tg.set_menu()
        confirmed = await tg.send(
            f"✅ Bot is online and connected.\n\n"
            f"Event: {cfg.event_name}\n"
            f"Watching for: {', '.join(cfg.match_keywords)}"
            f"{f' up to £{cfg.max_price:g}' if cfg.max_price else ''}\n"
            f"Checking every ~{cfg.interval}s.\n\n"
            f"Tap 🔍 Check now to test it.",
            KEYBOARD,
        )
        if not confirmed:
            sys.exit(
                "Could not message you on Telegram. Run test_telegram.bat "
                "(or python test_telegram.py) to see exactly why."
            )
        log.info("Telegram confirmed; watching %s", cfg.event_url)
        await asyncio.gather(w.loop(), w.handle_commands())


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
