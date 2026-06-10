# PS5 Availability Tracker 🎮

Tracks product availability (PS5 by default, but anything configurable) across
India's major e-commerce and quick-commerce platforms, across **multiple
pincodes**, and reports each run to **Telegram**.

**Platforms covered:** Blinkit · Zepto · Swiggy Instamart · BigBasket · Amazon · Flipkart

---

## How it works

For every **platform × product × location** combination, the tracker checks
whether the product is in stock and collects price + (for quick-commerce) the
delivery ETA. Results are formatted into one Telegram message per run.

- **Quick-commerce** (Blinkit / Zepto / Instamart / BigBasket) is queried via
  each platform's internal JSON API. These serve results by **latitude/longitude**,
  not pincode — so each location in `config.yaml` needs `lat`/`lon`.
- **Amazon / Flipkart** are queried with a **headless browser** (Playwright),
  because they block plain HTTP clients. These only need a pincode.

```
run.py ──► runner ──► [ platform checker × product × location ] ──► Telegram
                          (async, rate-limited, isolated failures)
```

---

## ⚠️ Read this first — expectations

None of these platforms offers a public/supported API. The tracker relies on
**internal endpoints and page structure that the platforms change without
notice**, and several actively fight scraping (rotating CSS classes, bot
detection, geo-gating). Practical implications:

- Expect to **occasionally re-check selectors/endpoints** when a platform stops
  returning results. Each platform lives in its own file under
  `ps5tracker/platforms/` with comments on what to verify (open the site in your
  browser's DevTools → Network and copy the updated request).
- A failing platform is **isolated** — it reports `⚠️ ERROR` for that platform
  and the rest of the run still completes and notifies.
- Run **infrequently** (every 6h / twice a day, as you planned) and keep the
  built-in delays — hammering these sites gets your IP blocked.
- This is for **personal availability monitoring**. Respect each platform's
  terms of service.

---

## Setup

```bash
cd ps5-tracker
uv sync
uv run playwright install chromium
[ -f .env ] || cp .env.example .env
```

If you do not have `uv` installed yet, `./scripts/setup.sh` can still create
`.venv` with `pip` as a fallback. When `uv` is available, that script runs the
same `uv sync` + Playwright setup commands for you.

Then:

### 1. Telegram credentials → `.env`
The setup command above copies `.env.example` to `.env` if needed. Fill in:

- `TELEGRAM_BOT_TOKEN` — message [@BotFather](https://t.me/BotFather), send
  `/newbot`, copy the token.
- `TELEGRAM_CHAT_ID` — message your new bot once, then open
  `https://api.telegram.org/bot<TOKEN>/getUpdates` and read `chat.id`.
  (For a group: add the bot to the group, send a message, then check `getUpdates`.)

Verify it works:
```bash
uv run ps5-tracker --test-telegram
```

### 2. Products & locations → `config.yaml`
- **`products`**: the default tracks the PS5 console (and excludes accessories
  via the `exclude` list). Add your own products here — give me the list and
  drop them in.
- **`locations`**: add each pincode you want to monitor **with its lat/lon**
  (look up once: search "`<area> latitude longitude`"). Quick-commerce needs the
  coordinates; Amazon/Flipkart use the pincode.
- **`notifications.notify_mode`**:
  - `always` — full report every run (good while setting up)
  - `on_available` — only ping when something is in stock
  - `on_change` — only ping when availability changes vs. the last run

### 3. Try a dry run (no Telegram send)
```bash
uv run ps5-tracker --dry-run
# or limit platforms:
uv run ps5-tracker --dry-run --platform amazon --platform blinkit
```

---

## Scheduling (every 6 hours / twice a day)

The script is a plain one-shot command, so use **cron** (macOS/Linux). Edit your
crontab:

```bash
crontab -e
```

**Every 6 hours** (00:00, 06:00, 12:00, 18:00):
```cron
0 */6 * * * /Users/shobhit/personal/ps5-tracker/scripts/run_tracker.sh
```

**Twice a day** (10:00 AM and 8:00 PM):
```cron
0 10,20 * * * /Users/shobhit/personal/ps5-tracker/scripts/run_tracker.sh
```

`run_tracker.sh` runs `uv run ps5-tracker` when `uv` is available, otherwise it
activates `.venv`, runs one pass, and appends output to `tracker.log` in the
project folder. Check that file to debug scheduled runs.

> **macOS note:** cron needs Full Disk Access on recent macOS. If cron jobs
> silently don't run, grant `/usr/sbin/cron` Full Disk Access in
> System Settings → Privacy & Security. Alternatively use a `launchd` plist —
> ask me and I'll generate one.

---

## CLI reference

| Command | What it does |
|---|---|
| `uv run ps5-tracker` | Run all checks, notify per config |
| `uv run ps5-tracker --dry-run` | Run checks, print report, **don't** send |
| `uv run ps5-tracker --test-telegram` | Send a test message and exit |
| `uv run ps5-tracker --platform zepto --platform amazon` | Restrict to specific platforms |
| `uv run ps5-tracker -v` | Verbose logging |

`python run.py ...` still works from the project root if you already have an
activated environment.

---

## Project layout

```
ps5-tracker/
├── config.yaml              # WHAT/WHERE to track (edit this)
├── .env                     # secrets: Telegram token + chat id (you create)
├── run.py                   # CLI entrypoint
├── pyproject.toml           # uv / package metadata
├── .python-version          # default Python for uv
├── requirements.txt
├── scripts/
│   ├── setup.sh             # one-time install
│   └── run_tracker.sh       # cron wrapper
└── ps5tracker/
    ├── config.py            # loads config.yaml + .env
    ├── models.py            # Product / Location / Result / Stock
    ├── notifier.py          # Telegram formatting + send
    ├── runner.py            # orchestration + notify policy + state
    └── platforms/
        ├── base.py          # PlatformChecker ABC (isolates failures)
        ├── blinkit.py       # ─┐
        ├── zepto.py         #  ├ quick-commerce, internal JSON APIs
        ├── instamart.py     #  │  (need lat/lon)
        ├── bigbasket.py     # ─┘
        ├── amazon.py        # ─┐ headless browser (Playwright)
        └── flipkart.py      # ─┘  (need pincode)
```

## Adding a platform

Create `ps5tracker/platforms/yourplatform.py` subclassing `PlatformChecker`,
implement `async def _check(self, product, location) -> list[Result]`, and
register it in `ps5tracker/platforms/__init__.py`. The base class handles error
isolation and the "not listed" fallback for you.
