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

# Release metadata (helps debugging production issues)
GIT_SHA="unknown"
GIT_BRANCH="unknown"
GIT_DIRTY="null"
if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
    GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
    GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
    if [ -n "$(git status --porcelain 2>/dev/null || true)" ]; then
        GIT_DIRTY="true"
    else
        GIT_DIRTY="false"
    fi
fi

BUILD_TIME_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "$BUILD_DIR/RELEASE_META.json" <<EOF
{
  "artifact_name": "${ARTIFACT_NAME}",
  "build_time_utc": "${BUILD_TIME_UTC}",
  "git_sha": "${GIT_SHA}",
  "git_branch": "${GIT_BRANCH}",
  "git_dirty": ${GIT_DIRTY}
}
EOF

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

# Copy encrypted secrets (if exists)
if [ -f ".env.enc" ]; then
    echo "Copying encrypted secrets (.env.enc)..."
    cp .env.enc "$BUILD_DIR/"
else
    echo "Warning: .env.enc not found. Server will need .env manually or from previous release."
fi

# Create tarball
echo "Creating tarball..."
tar -czf "$ARTIFACT_NAME" -C "$BUILD_DIR" .

# Cleanup
rm -rf "$BUILD_DIR"

echo "Artifact created: $ARTIFACT_NAME"
