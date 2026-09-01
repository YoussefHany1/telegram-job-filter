# Telegram Job Filter & Forwarding System

A personal Telethon **userbot** (runs as your own Telegram account, not a
bot) that watches job channels you're a member of - including ones you
don't own or administrate - filters new posts by keywords you define, and
forwards only the matches to your Saved Messages. Duplicates are never
forwarded twice, and everything (channels, keywords, filter mode) can be
managed live, from Saved Messages, without restarting the app.

## Contents

1. [Python installation](#1-python-installation)
2. [Getting Telegram API credentials](#2-getting-telegram-api-credentials)
3. [Virtual environment](#3-virtual-environment)
4. [Installing dependencies](#4-installing-dependencies)
5. [Configuring .env](#5-configuring-env)
6. [First login](#6-first-login)
7. [Adding channels](#7-adding-channels)
8. [Adding keywords](#8-adding-keywords)
9. [Adding exclude keywords](#9-adding-exclude-keywords)
10. [Running the application](#10-running-the-application)
11. [Admin commands (Saved Messages)](#11-admin-commands-saved-messages)
12. [Troubleshooting](#12-troubleshooting)
13. [Keeping it running continuously](#13-keeping-it-running-continuously)
14. [Running the tests](#14-running-the-tests)
15. [Project structure](#15-project-structure)

---

## 1. Python installation

Requires **Python 3.11+**.

- **macOS**: `brew install python@3.11`, or download from [python.org](https://www.python.org/downloads/)
- **Windows**: download the installer from [python.org](https://www.python.org/downloads/) - check "Add Python to PATH" during install
- **Linux**: usually preinstalled; otherwise `sudo apt install python3.11 python3.11-venv` (Debian/Ubuntu) or your distro's equivalent

Verify with:
```bash
python3 --version
```

## 2. Getting Telegram API credentials

1. Go to <https://my.telegram.org> and log in with your phone number.
2. Open **API Development Tools**.
3. Fill in any app name/description (these are just labels, e.g. "Job Filter Bot").
4. You'll get an **`api_id`** (a number) and an **`api_hash`** (a long hex string) - you'll need both in step 5.

## 3. Virtual environment

From the project folder:
```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
```
You'll know it worked when your shell prompt shows `(.venv)`.

## 4. Installing dependencies

```bash
pip install -r requirements.txt
```
(For running the test suite too, also run `pip install -r requirements-dev.txt` - see [section 14](#14-running-the-tests).)

## 5. Configuring .env

Copy the example file and fill it in:
```bash
cp .env.example .env
```
Open `.env` in an editor:
```env
API_ID=your_api_id_from_step_2
API_HASH=your_api_hash_from_step_2
PHONE=+201234567890          # your number, international format, no spaces
SESSION_NAME=job_filter_session
DB_PATH=data/job_filter.db
LOG_LEVEL=INFO
```
`.env` is git-ignored - it never gets committed, and neither does the database or session file.

## 6. First login

Run the app:
```bash
python app.py
```
On the **first run only**, you'll be prompted right in the terminal:
```
Enter the Telegram verification code you received:
```
Telegram sends this as a message to your account (check the Telegram app on another device, or Saved Messages/official Telegram service notifications). Type the code and press Enter.

If you have **Two-Factor Authentication** enabled, you'll also be asked for your password.

Once logged in, Telethon saves a `job_filter_session.session` file locally - every future run reuses it silently, no code/password needed again unless that file is deleted or the session is revoked.

## 7. Adding channels

Once the app is running, open **Saved Messages** in Telegram (any device) and send:
```
/addchannel @some_job_channel
```
You can use:
- A public `@username`
- A numeric Telegram ID (useful for channels without a username)

The bot validates the channel is reachable and replies with confirmation or a clear error (private/inaccessible, invalid username, etc.) - it never crashes on a bad channel.

Other channel commands:
```
/removechannel @some_job_channel
/enablechannel @some_job_channel
/disablechannel @some_job_channel
/channels                       # lists all configured channels + status
```

## 8. Adding keywords

Also from Saved Messages:
```
/addkeyword React Native
/addkeyword Expo
/addkeyword Flutter
/keywords                       # lists current include keywords
/removekeyword Flutter
```
By default, **any one** keyword matching is enough to forward a post (OR mode). To require **all** keywords to be present instead:
```
/mode and
```
Switch back anytime with `/mode or`.

## 9. Adding exclude keywords

```
/addexclude Senior
/addexclude Manager
/addexclude Internship
/excludes                       # lists current exclude keywords
/removeexclude Senior
```
A post is only forwarded if it matches your include rule **and** contains none of your exclude keywords.

You can also pause forwarding entirely without clearing your keyword lists:
```
/filter off
/filter on
```

## 10. Running the application

```bash
source .venv/bin/activate
python app.py
```
Expected startup output:
```
Loading configuration...
Connecting to Telegram...
Checking session...
Connected successfully
Initializing database...
Loading enabled channels...
Loading filters...
Starting listeners...
System is running.

Waiting for new jobs...
```
When a matching post appears in a monitored channel, you'll see it forwarded to Saved Messages within moments, formatted like:
```
🔥 MATCHED JOB

📢 Source: @example_channel
🔑 Matched Keyword: React Native

🕒 2026-08-29 14:20

--------------------

React Native Developer
Remote
Full-time
...

--------------------

🔗 Original Post:
https://t.me/example_channel/1234
```
Stop the app anytime with `Ctrl+C`.

## 11. Admin commands (Saved Messages)

For security, **all admin commands only work when sent from your own account to Saved Messages** - no other chat can control the bot, even if it somehow ended up in a group the account is in.

| Command | What it does |
|---|---|
| `/addchannel <@channel\|id>` | Add and validate a source channel |
| `/removechannel <@channel\|id>` | Remove a channel |
| `/enablechannel <@channel\|id>` | Resume monitoring a channel |
| `/disablechannel <@channel\|id>` | Pause monitoring without removing it |
| `/channels` | List all configured channels and their status |
| `/addkeyword <keyword>` | Add an include keyword |
| `/removekeyword <keyword>` | Remove an include keyword |
| `/keywords` | List include keywords |
| `/addexclude <keyword>` | Add an exclude keyword |
| `/removeexclude <keyword>` | Remove an exclude keyword |
| `/excludes` | List exclude keywords |
| `/filter on` / `/filter off` | Pause/resume forwarding entirely |
| `/mode and` / `/mode or` | Switch keyword matching mode |
| `/help` | Show the command list |

## 12. Troubleshooting

- **"Missing required environment variable"** - `.env` is missing `API_ID`, `API_HASH`, or `PHONE`. Check `.env.example` for the expected format.
- **Stuck / wrong code entered on login** - delete `job_filter_session.session` (or whatever `SESSION_NAME` you set) and re-run `python app.py` to restart the login flow.
- **"Channel is private or inaccessible"** when adding a channel - your account isn't a member of that channel; join it first (from any Telegram client), then retry `/addchannel`.
- **Nothing gets forwarded** - check `/keywords` isn't empty and `/filter` is `on`; also check `/channels` shows the channel as 🟢 enabled.
- **App exits instead of reconnecting after a network drop** - it retries automatically for a while (Section 23); if your connection was down longer than that, just re-run `python app.py`.
- **FloodWaitError in the logs** - Telegram is rate-limiting the account; the app waits it out automatically and resumes - no action needed unless it keeps recurring, in which case reduce how often you're adding channels/keywords in a short period.
- **General crash/traceback** - check the log output for the `[ERROR]` line right above it; a single bad message or command is designed to never take down the whole app, so a crash here is worth reporting/investigating rather than just restarting.

## 13. Keeping it running continuously

The app is a plain long-running Python process - pick whichever fits your setup:

- **Linux (systemd)** - create `/etc/systemd/system/job-filter.service`:
  ```ini
  [Unit]
  Description=Telegram Job Filter
  After=network.target

  [Service]
  WorkingDirectory=/path/to/telegram-job-filter
  ExecStart=/path/to/telegram-job-filter/.venv/bin/python app.py
  Restart=always
  RestartSec=10

  [Install]
  WantedBy=multi-user.target
  ```
  Then: `sudo systemctl enable --now job-filter`

- **tmux / screen** (simplest, any OS with a terminal): start a session, run `python app.py` inside it, detach (`Ctrl+B D` for tmux, `Ctrl+A D` for screen) - it keeps running after you close your terminal/SSH session.

- **pm2** (if you have Node.js around): `pm2 start "python app.py" --name job-filter --interpreter none`

- **Docker**: not included by default (kept out per "no unnecessary dependencies/complexity" for v1), but the app has no OS-specific dependencies, so a minimal `python:3.11-slim` image + `pip install -r requirements.txt` + `CMD ["python", "app.py"]` works if you prefer that route. Mount `data/` and the `.session` file as a volume so they persist across container restarts.

Whichever you choose, make sure `.env`, the `.session` file, and `data/` persist across restarts - only the Python process itself needs to restart, not the login or your configured channels/keywords.

## 14. Running the tests

```bash
pip install -r requirements-dev.txt
pytest -v
```
Covers the filter engine (all Section 28 cases + AND/OR + Arabic text), the text normalizer, and the DB-backed keyword/channel services (live add/remove, mode switching, duplicate prevention) - 32 tests, no live Telegram connection required.

## 15. Project structure

```
telegram-job-filter/
├── app.py                    # entry point - wires everything together
├── config.py                 # loads/validates .env
├── requirements.txt          # runtime dependencies
├── requirements-dev.txt      # + pytest, for running tests
├── pytest.ini
├── .env.example
├── .gitignore
├── README.md
│
├── database/
│   ├── db.py                 # connection lifecycle
│   ├── models.py             # SQL schema (all tables)
│   └── repositories.py       # all raw SQL lives here
│
├── tg/
│   ├── client.py              # Telethon client + login
│   ├── listeners.py           # real-time message pipeline
│   ├── sender.py               # job formatting + forwarding
│   └── commands.py             # Saved-Messages-only admin commands
│
├── filters/
│   ├── normalizer.py           # text preprocessing (Unicode/Arabic-safe)
│   ├── rules.py                 # pure keyword-matching primitives
│   └── engine.py                 # composes normalizer + rules
│
├── services/
│   ├── channel_service.py       # channel business logic + cache
│   ├── keyword_service.py        # keyword business logic + cache
│   └── message_service.py         # filter orchestration + duplicate prevention
│
├── utils/
│   ├── logger.py                  # structured logging setup
│   └── helpers.py                  # FloodWait-aware retry helper
│
└── tests/                            # 32 unit tests, no live Telegram needed
```

### Possible future extensions (not in v1, architecture allows for them)

Web dashboard, multiple forward destinations, true keyword groups (Section 18's schema hook already exists via per-call include/exclude lists), a scoring system, regex filters, AI-based classification, salary/location/remote-only filters, semantic duplicate detection, analytics.
