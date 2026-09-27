# AXS UK resale ticket watcher (Telegram bot)

Watches an AXS UK event page for **resale standing tickets** and sends a Telegram
alert (with a screenshot and a link) the moment one is listed, so you can
grab it from your phone.

> **Why it alerts instead of auto-buying:** AXS checkout sits behind a queue,
> bot checks and a logged-in payment step. Automating the purchase breaks
> AXS's terms and gets accounts cancelled. Resale tickets usually last
> 30–120 seconds, and a phone alert plus the AXS app open and logged in is
> fast enough.

---

## Step 1: Install the prerequisites

You need **Python 3.11+** on a computer that can stay on while you watch, such
as your laptop, a Raspberry Pi or a cheap UK VPS.

```bash
cd axs-resale-bot
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install --with-deps chromium   # on Windows/macOS: playwright install chromium
```

## Step 2: Create your Telegram bot

1. In Telegram, open a chat with **@BotFather**.
2. Send `/newbot`, then pick a name and a username that ends in `bot`.
3. BotFather replies with a **token** like `123456789:AA...`. Keep it secret.

```bash
cp .env.example .env
```

Open `.env` and paste the token into `TELEGRAM_BOT_TOKEN=`.

## Step 3: Get your chat id

1. Open your new bot in Telegram, press **Start** and send it any message.
2. Run:

   ```bash
   python get_chat_id.py
   ```

3. Copy the printed `TELEGRAM_CHAT_ID=...` line into `.env`.

The bot only answers commands from this chat id, so strangers can't control it.

## Step 4: Find the event URL

1. On **axs.com/uk**, open your show's event page, which is the page where
   you'd pick tickets and where resale listings appear.
2. Copy the URL from the address bar into `AXS_EVENT_URL=` in `.env`.

## Step 5: Tell it what to look for

In `.env`:

| Setting | What it does | Example |
|---|---|---|
| `MATCH_KEYWORDS` | Words in the ticket name. A listing matches when it has one of these **and a £ price**. | `standing,general admission` |
| `MAX_PRICE` | Optional price cap in £. Leave it blank for any price. | `120` |
| `CHECK_INTERVAL` | Seconds between checks (minimum 30). | `60` |
| `CHECK_JITTER` | Random extra 0–N seconds, so checks don't look robotic. | `20` |

**Tip:** look at how AXS labels your ticket type on the page (for example
"GA Standing", "Standing Floor" or "Pitch Standing") and put that wording in
`MATCH_KEYWORDS`.

## Step 6: First run (visible browser)

Set `HEADLESS=false` in `.env`, then:

```bash
python bot.py
```

A Chrome window opens on the event page. If AXS shows a cookie banner, a
queue or a "verify you are human" check, deal with it by hand in that window.
Cookies are saved in `browser-profile/`, so later runs look like a returning
visitor.

In Telegram you should get **"✅ Watching …"**. Send `/check`, and you should get
either "nothing matching right now" or an alert. Send `/shot` to see exactly
what the bot sees.

## Step 7: Leave it running

Set `HEADLESS=true` and start it again. To keep it running after you close the
terminal:

- **Mac/Linux:** `nohup python bot.py > bot.log 2>&1 &` (or use `tmux`/`screen`)
- **Windows:** leave the terminal open, and turn off sleep in power settings

Run it from a **UK home connection** if you can. Datacenter or VPS IP
addresses get bot checks much more often.

## Step 8: Be ready to buy

- Install the **AXS app** on your phone and stay logged in, with your card saved.
- Give the Telegram bot chat a loud, distinct notification sound and let it
  override Do Not Disturb.
- When the alert arrives, tap the link and check out. Someone else may be
  trying for the same ticket, so be quick.

---

## Telegram commands

| Command | Action |
|---|---|
| `/status` | Watching or paused, last check time and result, settings |
| `/check` | Run a check right now |
| `/shot` | Screenshot of the page as the bot sees it |
| `/pause` / `/resume` | Stop or start checking |
| `/help` | List commands |

## What the alerts mean

- **🎟️ RESALE TICKETS FOUND!** A matching listing with a price is on the page.
  You get the matching lines, the link and a full-page screenshot. You won't
  get the same alert again until the listings change.
- **Listings gone.** The listing disappeared, probably because someone bought it.
- **🚧 queue / bot check.** AXS is blocking or queueing the bot. It keeps
  retrying. If this doesn't clear, raise `CHECK_INTERVAL`, or run once with
  `HEADLESS=false` and solve the check by hand.
- **⚠️ 5 checks failed.** Network or page errors. Check your connection.

## Troubleshooting

- **Never alerts, but I can see tickets on the site:** send `/shot`. If the
  screenshot shows the tickets, your `MATCH_KEYWORDS` don't match AXS's wording.
  Copy the wording exactly as the page shows it. If the screenshot doesn't show
  tickets, resale may be on a different page (for example a "Resale" tab or
  button). Open that page yourself and use its URL as `AXS_EVENT_URL`.
- **False alerts:** make `MATCH_KEYWORDS` more specific, or set `MAX_PRICE`.
- **`Executable doesn't exist`:** run `playwright install chromium` again.

## Tests

```bash
pip install pytest
python -m pytest tests
```
