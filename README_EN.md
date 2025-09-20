# Progresser — Telegram Bot with a Publishing Progress Bar

A Telegram bot that schedules posts to a channel and shows a live progress bar until publishing. Designed to build anticipation before content drops.

## Key Features

- ⏳ Live progress bar in the channel (edits one message)
- 📝 Text post or 📷 photo with caption
- ⏱ Presets: 1/5/10 minutes or custom duration
- ♻️ Survives restarts: resumes bars after bot restart (SQLite)
- ❌ Cancel any scheduled job via `/cancel` (shows progress and time left)
- 🔐 `/check_add` verifies real capabilities (send/edit/delete) with clear report
- 🌐 i18n: Russian (default) and English (`--language en`)
- 🐳 Ready for Docker + docker-compose (auto-restart, DB persistence)

## Stack

- Python 3.10+, `python-telegram-bot` v22
- `python-dotenv`
- SQLite (jobs persistence)
- Docker, Docker Compose

## How It Works

1) Send `/run` and provide text and/or photo.
2) Pick the desired duration.
3) The bot posts a message with a progress bar and updates it.
4) When complete, it deletes the bar and publishes your content.

## Quick Start

### A) Docker Compose (recommended)

1. Create `.env` in project root:
```
BOT_TOKEN="YOUR_BOT_TOKEN_HERE"
CHANNEL_ID="YOUR_CHANNEL_ID_HERE"
```

Tip: If you don’t know your channel ID, send your channel to @username_to_id_bot — it will return the numeric ID (usually starts with `-100`).

2. Start:
```bash
docker compose up -d --build
```

3. Logs:
```bash
docker compose logs -f
```

4. Stop:
```bash
docker compose down
```

Notes:
- The DB is persisted by binding `./jobs.db` to `/app/jobs.db`.
- The service uses `restart: unless-stopped`.

### B) Docker

```bash
docker build -t progress-bar-bot .
docker run -d --env-file .env progress-bar-bot
```

Or pass env vars directly:
```bash
docker run -d \
  -e BOT_TOKEN="YOUR_BOT_TOKEN_HERE" \
  -e CHANNEL_ID="YOUR_CHANNEL_ID_HERE" \
  progress-bar-bot
```

### C) Local

```bash
pip install -r requirements.txt
echo 'BOT_TOKEN=YOUR_BOT_TOKEN_HERE' > .env
echo 'CHANNEL_ID=YOUR_CHANNEL_ID_HERE' >> .env
python bot.py
```

## Commands

- `/start` — welcome and help
- `/run` — schedule a post with a progress bar
- `/cancel` — list/cancel active schedules
- `/check_add` — verify channel permissions (send/edit/delete tests)

## Language

Default UI language is Russian. Switch to English with:
```bash
python bot.py --language en
```

Docker:
```bash
docker run --rm -it --env-file .env progress-bar-bot python bot.py --language en
```

Compose:
```bash
docker compose run --rm bot python bot.py --language en
```

## Internals

- Jobs are stored in SQLite (`jobs` table) with fields: `id, chat_id, message_id, post_text, media(json), duration, start_time, status`.
- Cancellation marks job as `cancelled`; the progress loop checks status and exits cleanly.
- On startup, the bot resumes all `active` jobs.
- Progress updates are paced to avoid hitting edit limits.
 
## License

MIT — see `LICENSE`.
