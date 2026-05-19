# Telegram Voice Transcriber Bot (Local transcription)

> All the transcription happens locally on your machine, so you don't have to pay for any cloud service.

A Python bot that listens to voice messages on Telegram, transcribes them locally using Whisper, and saves transcriptions with timestamps.

## Latest Updates

**2026-05-19**: Refactored transcription to run in a subprocess so memory is automatically released after each transcription. Models are still cached on disk by HuggingFace, so subsequent transcriptions load quickly. This reduces idle memory footprint for bots with sporadic usage patterns.

**2026-05-14**: Switched transcription backend from `openai-whisper` (CPU) to `mlx-whisper` (Apple Silicon GPU/Neural Engine). Benchmarks on real messages: **1.5–1.6× faster on ~6-minute clips** (13s vs 20–21s end-to-end), and **2.8× faster on 1-minute clips** (8.3s vs 23.2s transcription-only, `small` model). Actual transcription speedup is higher since end-to-end times include a fixed Telegram file download overhead. Note: this makes the bot **Apple Silicon only** — see [Windows/Linux](#windowslinux) below if you need cross-platform support.

**2026-05-02**: Each transcription now includes a `token_count` field (tiktoken) in its frontmatter — useful for batching transcriptions into large-context LLMs without hitting token limits.

**2026-05-01**: Added real-time status notifications — bot now sends messages when audio is received, transcription starts, and when it completes or fails.

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
- **Apple Silicon Mac (M1 or later)** — required for mlx-whisper
- ffmpeg (required to decode audio): `brew install ffmpeg`
- Telegram bot token (get from [BotFather](https://t.me/botfather))

### Windows/Linux

The bot works on Windows and Linux with a small code change: swap `mlx-whisper` for `openai-whisper` in `requirements.txt`, and in `transcriber_worker.py` replace the `mlx_whisper.transcribe()` call with `whisper.load_model(...).transcribe(...)`. Everything else (Telegram polling, file saving, service management) is platform-agnostic. Performance will be slower since `openai-whisper` runs on CPU.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Pre-download Whisper Model

Models are downloaded from Hugging Face on first use and cached locally. Pre-download before starting the service to avoid a delay on the first transcription:

```bash
# base model (recommended, ~290MB)
python3 -c "import mlx_whisper; mlx_whisper.transcribe('/dev/null', path_or_hf_repo='mlx-community/whisper-base-mlx')"

# Other sizes: whisper-tiny-mlx, whisper-small-mlx, whisper-medium-mlx, whisper-large-mlx
# turbo (large-v3 distilled, fast + accurate):
python3 -c "import mlx_whisper; mlx_whisper.transcribe('/dev/null', path_or_hf_repo='mlx-community/whisper-large-v3-turbo')"
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
- `model`: Model size (tiny, base, small, medium, large, turbo)
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
- `token_count`: Token count of the transcribed text (tiktoken, ~1–3% accurate for English LLM batching)

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
- Pre-download the model: `python3 -c "import mlx_whisper; mlx_whisper.transcribe('/dev/null', path_or_hf_repo='mlx-community/whisper-base-mlx')"`
- Check disk space (large models need 1-3GB)

### Voice file not transcribing
- Check file size (should be < 25MB)
- Check logs for errors: `tail -f transcriber_data/logs/bot.log`
- Retry happens automatically (up to 3 times by default)

## License

MIT
