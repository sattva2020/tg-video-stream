#!/bin/bash

# Streamer entrypoint script
# Supports two modes:
#   STREAMER_MODE=multi  - Multi-channel mode with Redis control (default)
#   STREAMER_MODE=legacy - Single channel mode from env vars (original)

set -e

echo "Starting Telegram Streamer..."
echo "Mode: ${STREAMER_MODE:-multi}"

if [ "${STREAMER_MODE}" = "legacy" ]; then
    echo "Running in legacy single-channel mode..."
    exec python main.py
else
    echo "Running in multi-channel mode with Redis control..."
    exec python multi_channel_runner.py
fi
