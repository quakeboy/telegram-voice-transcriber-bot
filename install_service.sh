#!/bin/bash

# Helper script to install the Telegram Voice Transcriber Bot as a macOS launchd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH=$(which python3)
PLIST_FILE="$HOME/Library/LaunchAgents/com.local.transcriber.plist"

echo "📦 Telegram Voice Transcriber Bot - macOS Service Installer"
echo ""

if [ ! -f "$SCRIPT_DIR/bot.py" ]; then
    echo "❌ Error: bot.py not found in $SCRIPT_DIR"
    exit 1
fi

if [ -z "$PYTHON_PATH" ]; then
    echo "❌ Error: python3 not found in PATH"
    exit 1
fi

echo "✓ Found Python: $PYTHON_PATH"
echo "✓ Found bot.py: $SCRIPT_DIR/bot.py"
echo ""

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.local.transcriber</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$SCRIPT_DIR/bot.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/transcriber_data/logs/bot.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/transcriber_data/logs/bot.log</string>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

echo "✓ Created launchd plist: $PLIST_FILE"
echo ""

read -p "Load the service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    launchctl load "$PLIST_FILE"
    echo "✓ Service loaded"
    echo ""
    echo "To manage the service:"
    echo "  Start:   launchctl start com.local.transcriber"
    echo "  Stop:    launchctl stop com.local.transcriber"
    echo "  Status:  launchctl list | grep transcriber"
    echo "  Unload:  launchctl unload $PLIST_FILE"
    echo ""
    sleep 2
    echo "Service status:"
    launchctl list | grep transcriber || echo "  (service not running yet)"
else
    echo "⏭️  Service not loaded. To load manually, run:"
    echo "   launchctl load $PLIST_FILE"
fi
