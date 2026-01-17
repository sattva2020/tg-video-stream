# AyuGram Headless Engine for Sattva Streamer
#
# Multi-stage build for headless Telegram engine based on AyuGram
# Target: Linux x86_64
#
# Usage in Dokploy:
# 1. Create new "Application" service (not Compose)
# 2. Select "Dockerfile" as build type
# 3. Point to this file: tg-engine/Dockerfile

# =============================================================================
# Stage 1: Build Environment (based on Telegram's official CentOS image)
# =============================================================================
FROM ghcr.io/telegramdesktop/tdesktop/centos_env:latest AS builder

# Build arguments for Telegram API credentials
ARG TDESKTOP_API_ID
ARG TDESKTOP_API_HASH

# Verify API credentials are provided
RUN if [ -z "$TDESKTOP_API_ID" ] || [ -z "$TDESKTOP_API_HASH" ]; then \
    echo "ERROR: TDESKTOP_API_ID and TDESKTOP_API_HASH must be set"; \
    exit 1; \
    fi

USER root
WORKDIR /build

# Clone AyuGram with all submodules
RUN git clone --recursive --depth 1 https://github.com/AyuGram/AyuGramDesktop.git tdesktop

WORKDIR /build/tdesktop

# Build AyuGram Desktop
RUN /build/tdesktop/Telegram/build/docker/centos_env/build.sh \
    -D TDESKTOP_API_ID=${TDESKTOP_API_ID} \
    -D TDESKTOP_API_HASH=${TDESKTOP_API_HASH}

# =============================================================================
# Stage 2: Runtime Environment (minimal image)
# =============================================================================
FROM ubuntu:22.04 AS runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpulse0 \
    libasound2 \
    libxcb1 \
    libxkbcommon0 \
    libssl3 \
    libfontconfig1 \
    libfreetype6 \
    libjpeg62 \
    libpng16-16 \
    libwebp7 \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /opt/sattva-tg-engine

# Copy built binary from builder stage
COPY --from=builder /build/tdesktop/out/Release/AyuGram ./sattva-tg-engine

# Note: Telegram Desktop is mostly statically linked, no additional .so files needed
# Create lib directory for future extensions
RUN mkdir -p ./lib/

# Create data directory for session storage
RUN mkdir -p /data/tg-session

# Volume for persistent session data
VOLUME ["/data/tg-session"]

# Health check placeholder (will be implemented in Phase 3)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD test -f /opt/sattva-tg-engine/sattva-tg-engine || exit 1

# Default command (will be replaced with headless RPC server in Phase 2)
ENTRYPOINT ["/opt/sattva-tg-engine/sattva-tg-engine"]

# Labels
LABEL org.opencontainers.image.title="Sattva TG Engine"
LABEL org.opencontainers.image.description="Headless Telegram engine based on AyuGram"
LABEL org.opencontainers.image.source="https://github.com/AyuGram/AyuGramDesktop"
