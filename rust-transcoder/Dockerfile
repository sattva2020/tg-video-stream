# Stage 1: Build
FROM rust:1.75-bookworm AS builder

WORKDIR /app

# Install ffmpeg for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy Cargo files for dependency caching
COPY Cargo.toml Cargo.lock* ./

# Create dummy main.rs to build dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs

# Build dependencies (cached layer)
RUN cargo build --release && rm -rf src

# Copy actual source
COPY src ./src

# Touch main.rs to force rebuild
RUN touch src/main.rs

# Build release binary
RUN cargo build --release

# Stage 2: Runtime
FROM debian:bookworm-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy binary from builder
COPY --from=builder /app/target/release/rust-transcoder /app/rust-transcoder

# Create non-root user
RUN useradd -r -s /bin/false transcoder && \
    chown -R transcoder:transcoder /app

USER transcoder

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

EXPOSE 8090

ENV RUST_LOG=info

CMD ["/app/rust-transcoder"]
