# Quick Start Guide

Get your Telegram voice transcriber running in 5 minutes.

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Download Whisper Model

```bash
# This downloads ~140MB (takes 1-2 min)
python -c "import whisper; whisper.load_model('base')"
```

If you have a smaller/larger model preference:
```bash
# tiny (39MB, faster)
python -c "import whisper; whisper.load_model('tiny')"

# large (2.9GB, more accurate)
python -c "import whisper; whisper.load_model('large')"
```

## Step 3: Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/start`
3. Send `/newbot`
4. Follow the prompts (choose a name, username)
5. Copy the token (looks like: `123456789:ABCDEFGHijklmnopqrstuvwxyz`)

## Step 4: Configure Bot

Edit `config.yaml` and set:
```yaml
telegram:
  bot_token: "PASTE_YOUR_TOKEN_HERE"
```

Optional: Add user whitelist:
```yaml
telegram:
  allowed_user_ids: [123456789, 987654321]  # Your Telegram user ID(s)
```

To find your Telegram ID, message [@userinfobot](https://t.me/userinfobot)

## Step 5: Test It

```bash
python bot.py
```

You should see:
```
2026-04-23 16:05:30 - transcriber - INFO - Whisper model 'base' loaded successfully
2026-04-23 16:05:30 - transcriber - INFO - Bot started, polling every 5 seconds...
```

Send a voice message to your bot on Telegram. Within 10-30 seconds, you should see:
```
2026-04-23 16:05:45 - transcriber - INFO - Received voice from @username (ID: 123456)
2026-04-23 16:06:10 - transcriber - INFO - Transcription complete: 04-23-16-06-10
```

Check the output:
```bash
ls transcriber_data/transcriptions/
# You should see: 04-23-16-06-10.md and 04-23-16-06-10.yaml
cat transcriber_data/transcriptions/04-23-16-06-10.md
```

## Step 6: Run in Background

**Option A: Simple nohup (keep running till you restart Mac)**
```bash
nohup python bot.py > transcriber_data/logs/bot.log 2>&1 &
```

**Option B: macOS Service (auto-start on login)**
```bash
./install_service.sh
```

Then manage with:
```bash
launchctl start com.local.transcriber    # Start
launchctl stop com.local.transcriber     # Stop
tail -f transcriber_data/logs/bot.log    # Watch logs
```

## Done! 🎉

Your bot is now transcribing voice messages locally. All data stays on your Mac.

## Troubleshooting

**"No such file or directory: config.yaml"**
- Make sure you're in the bot directory when running `python bot.py`

**"Bot token not configured"**
- Did you edit config.yaml with your real token?

**"Whisper model not found"**
- Run: `python -c "import whisper; whisper.load_model('base')"`

**"Received voice from X but no transcription file"**
- Check logs: `tail -f transcriber_data/logs/bot.log`
- First transcription is slower (model loading)
- Check disk space if model is large

## What's Next?

See [README.md](README.md) for full configuration options and advanced features.
