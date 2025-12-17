#!/usr/bin/env bash
set -euo pipefail

# build_artifact.sh
# Builds the deployment artifact for the Telegram Video Streamer

# Configuration
ARTIFACT_NAME="telegram-deploy-$(date +%Y%m%d%H%M%S).tar.gz"
BUILD_DIR="temp_build"

echo "Building artifact: $ARTIFACT_NAME"

# Clean up previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy backend
echo "Copying backend..."
mkdir -p "$BUILD_DIR/backend"
cp -r backend/src "$BUILD_DIR/backend/"
cp -r backend/alembic "$BUILD_DIR/backend/"
cp backend/alembic.ini "$BUILD_DIR/backend/"
cp backend/requirements.txt "$BUILD_DIR/backend/"
cp backend/run.py "$BUILD_DIR/backend/"

# Copy frontend build
echo "Copying frontend..."
mkdir -p "$BUILD_DIR/frontend"
if [ -d "frontend/dist" ]; then
    cp -r frontend/dist "$BUILD_DIR/frontend/"
else
    echo "Error: frontend/dist not found. Please run 'npm run build' in frontend/ first."
    exit 1
fi

# Copy streamer
echo "Copying streamer..."
cp -r streamer "$BUILD_DIR/"

# Copy scripts
echo "Copying scripts..."
cp -r scripts "$BUILD_DIR/"

# Copy config
echo "Copying config..."
cp -r config "$BUILD_DIR/"

# Copy specs (needed for systemd units in deploy scripts)
echo "Copying specs..."
cp -r specs "$BUILD_DIR/"

# Copy docs
echo "Copying docs..."
cp -r docs "$BUILD_DIR/"

# Copy root files
echo "Copying root files..."
cp docker-compose.yml "$BUILD_DIR/"
cp README.md "$BUILD_DIR/"
if [ -f "requirements.txt" ]; then
    cp requirements.txt "$BUILD_DIR/"
elif [ -f "streamer/requirements.txt" ]; then
    cp streamer/requirements.txt "$BUILD_DIR/"
fi

# Create tarball
echo "Creating tarball..."
tar -czf "$ARTIFACT_NAME" -C "$BUILD_DIR" .

# Cleanup
rm -rf "$BUILD_DIR"

echo "Artifact created: $ARTIFACT_NAME"
