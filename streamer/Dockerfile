FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ffmpeg is required)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default: multi-channel runner with Redis control
# Set STREAMER_MODE=legacy to use old main.py
ENV STREAMER_MODE=multi

# Entrypoint script to select mode
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
