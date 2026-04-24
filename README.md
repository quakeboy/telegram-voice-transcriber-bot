# Telegram Voice Transcriber Bot (Local transcription)

> All the transcription happens locally on your machine, so you don't have to pay for any cloud service.

A Python bot that listens to voice messages on Telegram, transcribes them locally using Whisper, and saves transcriptions with timestamps.

## Why?

- Can be used as a personal voice journaling bot. Has to be paired with an LLM for summarizing.
- Each transcript is saved as its own file with the timestamp and front matter which also has more information. So you can use this to create content on the fly if you pair it up with your daily workflow to either do a vlog or even other forms of content creation.
- You can pair it up with Claude Cowork so that it can scan the transcribed data at regular intervals and you can do various things with it.

## Features

- 🎙️ Listens for voice messages on Telegram
- 🤐 Transcribes locally (no cloud API)
- ✋ User whitelist (optional)
- 🔄 Automatic retry with exponential backoff
- 📁 FIFO audio buffer (keeps last N files)
- 📝 Transcriptions saved as `.md` with YAML metadata
- 🖥️ Runs as background service on macOS
- 📊 Rotating logs with configurable level

## Requirements

- Python 3.8+
- ffmpeg (required by Whisper to decode audio): `brew install ffmpeg`
- Telegram bot token (get from [BotFather](https://t.me/botfather))
- Whisper model pre-installed (see Setup)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download Whisper Model

```bash
# Download base model (recommended, ~140MB)
python -c "import whisper; whisper.load_model('base')"

# Or choose: tiny (39MB), small (77MB), medium (377MB), large (2.9GB)
python -c "import whisper; whisper.load_model('tiny')"
```

### 3. Configure Bot

Copy the example config and rename it:
```bash
cp config.yaml.example config.yaml
```

Then edit `config.yaml` with the following values:
```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN_HERE"  # Get from BotFather
  allowed_user_ids: [12345, 67890]   # Leave empty to allow all users
```

### 4. Run Bot

**Option A: Foreground (for testing)**
```bash
python bot.py
```

**Option B: Background (simple)**
```bash
nohup python bot.py > transcriber_data/logs/bot.log 2>&1 &
```

**Option C: macOS Service (recommended)**
```bash
./install_service.sh
```

## Configuration

### telegram
- `bot_token`: Your Telegram bot token (required)
- `polling_interval_seconds`: How often to check for messages (default: 5)
- `allowed_user_ids`: Whitelist of user IDs (empty = all users allowed)

### paths
- `workspace`: Root folder for all data (audio, transcriptions, logs)

### audio
- `max_files`: Keep only last N audio files (default: 20)
- `delete_failed_audio`: Delete audio if transcription fails (default: false)

### whisper
- `model`: Model size (tiny, base, small, medium, large)
- `language`: Language code (en, fr, es, etc.)
- `timeout_seconds`: Max transcription time per file

### retry
- `max_attempts`: Retry failed transcriptions N times
- `initial_backoff_seconds`: Wait time before first retry (1s, 2s, 4s... exponential)

### logging
- `level`: DEBUG, INFO, WARNING, ERROR
- `verbose_cleanup`: Log every deleted audio file

## File Structure

```
transcriber_data/
├── audio_fifo/        # Voice note audio (auto-deletes oldest)
├── transcriptions/    # .md files (transcriptions)
│   └── MM-DD-HH-MM-SS.yaml  # Metadata
└── logs/              # bot.log
```

## Metadata Saved

Each transcription has a YAML file with:
- `sender_name`: User's first name
- `sender_username`: Telegram username
- `sender_user_id`: User ID
- `telegram_timestamp`: When message was sent
- `audio_duration_seconds`: Voice note length
- `transcription_timestamp`: When transcription completed

## Manage Service (macOS)

```bash
# Start/stop
launchctl start com.local.transcriber
launchctl stop com.local.transcriber

# Check status
launchctl list | grep transcriber

# View logs
tail -f transcriber_data/logs/bot.log

# Unload (remove from auto-start)
launchctl unload ~/Library/LaunchAgents/com.local.transcriber.plist
```

## Troubleshooting

### Bot not running?
```bash
# Check if service loaded
launchctl list | grep transcriber

# Check logs
tail -f transcriber_data/logs/bot.log

# Manually start to see errors
python bot.py
```

### "Bot token not configured"
- Ensure `config.yaml` has a valid bot token (not the placeholder)

### Whisper model not found
- Download model: `python -c "import whisper; whisper.load_model('base')"`
- Check disk space (large models need 2-3GB)

### Voice file not transcribing
- Check file size (should be < 25MB)
- Check logs for errors: `tail -f transcriber_data/logs/bot.log`
- Retry happens automatically (up to 3 times by default)

## License

MIT
