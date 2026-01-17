#!/bin/bash
# =============================================================================
# Sattva TG Engine - AyuGram Build Script for Linux VPS
# Based on AyuGramDesktop fork of tdesktop
# Target: 37.53.91.144 (Dokploy) | Domain: sattva-streamer.top
# =============================================================================

set -e

# Configuration
BUILD_PATH="/opt/sattva-tg-engine"
AYUGRAM_REPO="https://github.com/AyuGram/AyuGramDesktop.git"
API_ID="${TDESKTOP_API_ID:-YOUR_API_ID}"
API_HASH="${TDESKTOP_API_HASH:-YOUR_API_HASH}"

echo "=========================================="
echo "Sattva TG Engine - AyuGram Build Setup"
echo "=========================================="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo or as root"
    exit 1
fi

# Step 1: Install prerequisites
echo "[1/5] Installing prerequisites..."
apt-get update
apt-get install -y \
    git \
    python3 \
    python3-pip \
    docker.io \
    docker-compose

# Enable and start Docker
systemctl enable docker
systemctl start docker

# Add current user to docker group (if not root)
if [ -n "$SUDO_USER" ]; then
    usermod -aG docker "$SUDO_USER"
fi

# Step 2: Create build directory
echo "[2/5] Creating build directory..."
mkdir -p "$BUILD_PATH"
cd "$BUILD_PATH"

# Step 3: Clone AyuGram with submodules
echo "[3/5] Cloning AyuGramDesktop..."
if [ -d "tdesktop" ]; then
    echo "Repository already exists, pulling latest..."
    cd tdesktop
    git pull
    git submodule update --init --recursive
else
    git clone --recursive "$AYUGRAM_REPO" tdesktop
    cd tdesktop
fi

# Step 4: Prepare libraries (builds Docker image)
echo "[4/5] Preparing libraries and Docker environment..."
./Telegram/build/prepare/linux.sh

# Step 5: Build the project
echo "[5/5] Building AyuGram (this may take 30-60 minutes)..."

# Create .env file for API credentials if not exists
if [ ! -f "../.env.build" ]; then
    cat > "../.env.build" << EOF
# Telegram API Credentials
# Get from https://my.telegram.org/
TDESKTOP_API_ID=$API_ID
TDESKTOP_API_HASH=$API_HASH
EOF
    echo "Created .env.build - please update with your API credentials!"
fi

# Source credentials
source "../.env.build"

# Build using Docker
docker run --rm -it \
    -u "$(id -u)" \
    -v "$PWD:/usr/src/tdesktop" \
    ghcr.io/telegramdesktop/tdesktop/centos_env:latest \
    /usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh \
    -D TDESKTOP_API_ID="$TDESKTOP_API_ID" \
    -D TDESKTOP_API_HASH="$TDESKTOP_API_HASH"

echo "=========================================="
echo "Build complete!"
echo "Binary location: $BUILD_PATH/tdesktop/out/Release/Telegram"
echo "=========================================="
