# AXS UK resale ticket watcher (Telegram bot)

Preset for **Asake, IN GOD WE TRUST WORLD TOUR, The O2 London, Thu 15 Oct 2026**
(AXS event `1457846`, <https://www.axs.com/uk/events/1457846/asake-tickets>),
watching for **standing** resale.

It checks the AXS page every minute or so. When a standing resale ticket is
listed, it sends you a Telegram alert with a **🎟️ BUY NOW** button, the listing
and a screenshot, so you can buy it on your phone.

> **Why it alerts instead of auto-buying:** AXS checkout sits behind a queue,
> bot checks and a logged-in payment step. Automating the purchase breaks
> AXS's terms and gets accounts cancelled. Resale tickets usually last
> 30–120 seconds, and a phone alert plus the AXS app open and logged in is
> fast enough.

---

## Run it from the web (recommended): GitHub Actions, every 5 minutes

This setup needs no RDP and no PC left on. GitHub's servers open the AXS
page every 5 minutes and message you on Telegram. Everything is set up on
github.com.

1. **Create the bot:** follow step 1 below (BotFather), then get your chat ID.
   The easiest way is to message **@userinfobot** in Telegram. It replies with
   your ID.
2. **Add the secrets:** on GitHub, open the repo → **Settings → Secrets and
   variables → Actions → New repository secret**. Add:
   - `TELEGRAM_BOT_TOKEN`: the token from BotFather
   - `TELEGRAM_CHAT_ID`: your chat ID
3. **Optional variables:** on the same page, open the **Variables** tab.
   - `AXS_EVENT_URL`: defaults to the Asake page. If the AXS Official Resale
     listings for the show are on a different page, paste that link here.
   - `MATCH_KEYWORDS`: defaults to `standing`.
   - `MAX_PRICE`: a price cap in £.
   - `EVENT_NAME`: the name shown in your Telegram messages.
4. **Put the workflow on the default branch:** scheduled workflows only run
   from `main`, so merge the PR that adds `.github/workflows/axs-resale-watch.yml`.
5. **Start it:** open the **Actions** tab, choose **AXS resale watch**, then
   click **Run workflow**. Within about 2 minutes Telegram should show
   **"✅ Bot is online (cloud, every ~5 min)"**. After that it runs by itself
   every 5 minutes.
6. **Stop it:** in the Actions tab, open **AXS resale watch**, click **⋯**
   and choose **Disable workflow**. Or tap **⏸ Pause** in Telegram.

How it behaves in this mode:
- The buttons (📊 Status, 🔍 Check now, 📸 Screenshot, ⏸ Pause, ▶️ Resume)
  still work, but the bot answers on its **next run**, within about 5 minutes.
- GitHub may start a scheduled run a few minutes late when it's busy, so
  "every 5 min" can sometimes be every 6–10 minutes.
- **Cost:** free on a **public** repo. On a **private** repo, each run uses
  about 2 of the 2,000 free minutes a month, which runs out in about 4 days.
  If this repo is private, put `axs-resale-bot/` and the workflow in a new
  public repo. Your token stays private in Secrets either way.
- AXS may show bot checks to GitHub's servers. If you keep getting 🚧
  messages, use the RDP or PC setup below instead, ideally on a UK home
  connection.

---

## Or run it on an RDP / PC

## Step 1: Create the bot in BotFather

1. In Telegram, open **@BotFather** and send `/newbot`.
2. Name: e.g. `Asake O2 Resale`. Username: must end in `bot`, e.g. `asake_o2_resale_bot`.
3. Copy the **token** it gives you (`123456789:AA...`). Keep it secret.
4. Optional: set the **Menu** in BotFather. The bot also sets this itself when it starts.
   Send `/setcommands`, pick your bot and paste:

   ```
   status - Watching or paused, last check
   check - Check for tickets right now
   shot - Screenshot of the page
   pause - Stop checking
   resume - Start checking again
   help - Show commands and buttons
   ```

5. Optional polish in BotFather: `/setdescription`, `/setuserpic`.
6. Open your new bot in Telegram, press **Start** and send it any message.
   You need this message for step 4.

## Step 2: Prepare the Windows RDP

On the RDP:

1. Install **Python 3.11 or newer** from <https://www.python.org/downloads/windows/>.
   Tick **"Add python.exe to PATH"** in the installer.
2. Copy the `axs-resale-bot` folder onto the RDP, e.g. to `C:\axs-resale-bot`.
   You can download the repo as a ZIP from GitHub, or use `git clone`.
3. Double-click **`install.bat`**. It creates a virtual environment, installs
   the packages and Chromium, and creates `.env`.

**Linux VPS instead of Windows:**

```bash
cd axs-resale-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
cp .env.example .env
```

## Step 3: Fill in `.env`

Open it with `notepad .env`. The Asake URL, event name and `standing`
keyword are already filled in. You only need to add:

| Setting | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the token from BotFather |
| `TELEGRAM_CHAT_ID` | from step 4 |
| `MAX_PRICE` | optional cap in £, e.g. `150`. Leave it blank for any price. |

Other settings: `CHECK_INTERVAL` is the number of seconds between checks
(default 60, minimum 30). `HEADLESS=false` shows the browser window.

## Step 4: Get your chat ID

With the token saved in `.env` and a message already sent to your bot
(step 1.6), double-click **`get_chat_id.bat`**. On Linux, run
`python get_chat_id.py`. Paste the `TELEGRAM_CHAT_ID=...` line into `.env`.

The bot ignores everyone except this chat ID.

## Step 5: First run and confirm it's working

1. For the first run, set `HEADLESS=false` in `.env` so you can see Chrome.
2. Double-click **`run.bat`**.
3. **Confirm in Telegram.** Within a few seconds the bot sends:

   > ✅ Bot is online and connected.
   > Event: Asake · The O2 London · Thu 15 Oct 2026
   > Watching for: standing …

   Buttons also appear under the chat box: **📊 Status · 🔍 Check now ·
   📸 Screenshot · ⏸ Pause · ▶️ Resume**.
4. Tap **📸 Screenshot**. You should see the Asake AXS page. If AXS shows a
   cookie banner, a queue or a "verify you are human" check, handle it in the
   Chrome window on the RDP. The cookies are remembered.
5. Tap **🔍 Check now**. The bot replies either "nothing matching right now"
   or with an alert.

If you get no confirmation message, the `run.bat` window shows why. Usually
the token or chat ID is wrong.

## Step 6: Leave it running

- Set `HEADLESS=true`, close the bot window and start `run.bat` again.
  `run.bat` restarts the bot automatically if it crashes.
- When you leave the RDP, **close the RDP window (disconnect). Don't sign
  out.** Signing out stops the bot.
- To start the bot automatically after the RDP reboots, press `Win+R`, type
  `shell:startup` and put a shortcut to `run.bat` in that folder.

## Step 7: Be ready to buy

- Install the **AXS app** on your phone and stay logged in, with your card saved.
- Give the Telegram bot chat a loud notification sound that overrides Do Not Disturb.
- When the alert arrives, tap **🎟️ BUY NOW ON AXS** and check out straight away.

---

## Buttons and commands

| Button | Command | Action |
|---|---|---|
| 📊 Status | `/status` | Watching or paused, last check time and result, settings |
| 🔍 Check now | `/check` | Run a check right now |
| 📸 Screenshot | `/shot` | Screenshot of the page as the bot sees it |
| ⏸ Pause / ▶️ Resume | `/pause` `/resume` | Stop or start checking |
| | `/help` or `/start` | Shows the buttons again |

## What the alerts mean

- **🎟️ RESALE TICKETS FOUND!** A standing listing with a £ price is on the page.
  You won't get the same alert again until the listings change.
- **Listings gone.** Someone probably bought it. The bot keeps watching.
- **🚧 queue / bot check.** AXS is blocking or queueing the bot. It keeps
  retrying. If this doesn't clear, raise `CHECK_INTERVAL`, or set
  `HEADLESS=false` and solve the check in the RDP's Chrome window.
- **⚠️ 5 checks failed.** Network or page errors.

## Troubleshooting

### No notifications on my phone

Double-click **`test_telegram.bat`** (or run `python test_telegram.py`). It
checks the `.env` file, token, chat ID and connection one by one, prints the
fix for the first problem it finds, and sends a test message if everything
is correct.

- **Test message arrives but the phone doesn't buzz:** it's a phone setting.
  Unmute the bot chat, turn on Telegram notifications (in Telegram and in the
  phone's settings), allow Telegram through Do Not Disturb or Focus, set
  battery use to Unrestricted on Android, and close Telegram Desktop or Web
  on the RDP, which takes the notifications instead of your phone.
- **Test works but no ticket alerts:** that's expected until a standing resale
  ticket is actually listed. Tap 📊 Status to check the bot is running.

- **Never alerts, but I can see standing tickets on AXS:** tap 📸 Screenshot.
  If the screenshot shows them, AXS's wording differs, so copy the exact label
  (e.g. `GA Standing`) into `MATCH_KEYWORDS`. If the screenshot doesn't show
  them, resale may be behind a "Resale" button or tab. Open that page on the
  RDP and use its URL as `AXS_EVENT_URL`.
- **Lots of 🚧 bot checks:** datacenter RDP IP addresses get flagged more
  often. Raise `CHECK_INTERVAL` to 90–120, or use an RDP or PC on a UK
  residential connection.
- **`Executable doesn't exist`:** run `python -m playwright install chromium`
  inside the virtual environment.

## Tests

```bash
pip install pytest
python -m pytest tests
```
