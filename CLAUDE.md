# Telegram Voice Transcriber Bot

A Telegram bot that polls for voice messages and transcribes them using OpenAI Whisper. Transcriptions are saved as Markdown files with YAML frontmatter.

## Running the bot

**Manually:**
```bash
python3 bot.py
```

**As a macOS launchd service** (install once):
```bash
bash install_service.sh
```

**Service management** (after install):
```bash
launchctl start com.local.transcriber
launchctl stop com.local.transcriber
launchctl list | grep transcriber   # check status
```

After any code change, restart the service — no reinstall needed:
```bash
launchctl stop com.local.transcriber && launchctl start com.local.transcriber
```

## Key files

| File | Purpose |
|------|---------|
| `bot.py` | Entry point — async polling loop |
| `telegram_handler.py` | Telegram API wrapper (async, python-telegram-bot v20+) |
| `transcriber.py` | Whisper model wrapper with exponential-backoff retry |
| `file_manager.py` | Saves audio files and transcription `.md` files; handles timezone conversion |
| `logger_config.py` | Rotating file + console logger setup |
| `config.yaml` | All runtime configuration |
| `install_service.sh` | Installs bot as a macOS launchd service |

## Configuration (`config.yaml`)

```yaml
telegram:
  bot_token: "..."             # BotFather token
  polling_interval_seconds: 5
  allowed_user_ids: []         # empty = allow all users

paths:
  workspace: "./transcriber_data"
  timezone_offset_hours: 4     # UTC offset for file timestamps (e.g. 4 = UTC+4)

audio:
  max_files: 20                # rotate oldest .ogg files beyond this count
  delete_failed_audio: false

whisper:
  model: "base"                # tiny / base / small / medium / large
  language: "en"
  timeout_seconds: 300

retry:
  max_attempts: 3
  initial_backoff_seconds: 1

logging:
  level: "INFO"
  verbose_cleanup: false
```

## Output structure

```
transcriber_data/
  audio_fifo/          # raw .ogg voice files (rotated)
    2026-04-24-10-29-31_username.ogg
  transcriptions/      # one .md per message
    2026-04-24-10-29-31.md
  logs/
    bot.log            # rotating log (10 MB × 5 backups)
```

Transcription files use YAML frontmatter:
```markdown
---
audio_duration_seconds: 12
sender_name: Raja
sender_username: rajavanya
sender_user_id: 123456789
telegram_timestamp: '2026-04-24 06:29:31+00:00'
transcription_timestamp: '1745486971.123'
---

Transcribed text goes here.
```

## Key conventions

- **Async API**: `python-telegram-bot` v20+ is fully async. All Telegram calls in `telegram_handler.py` use `await`. The main loop runs under `asyncio.run()`.
- **Timestamps**: Telegram sends UTC datetimes. `timezone_offset_hours` in config converts them to local time for filenames.
- **Single output file**: Transcriptions and metadata are stored together in one `.md` file (no separate `.yaml`).

## Dependencies

```bash
pip install -r requirements.txt
```

Requires: `python-telegram-bot>=20.0`, `openai-whisper>=20240314`, `pyyaml>=6.0`
