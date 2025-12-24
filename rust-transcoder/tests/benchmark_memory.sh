#!/usr/bin/env bash
# Benchmark: Memory usage при 10 concurrent streams
# Проверяет требование SC-002: память должна быть < 256MB при 10 concurrent streams

set -euo pipefail

echo "��� Memory Usage Benchmark - Rust Transcoder"
echo "==========================================="
echo ""

# Проверяем что docker compose доступен
if ! docker compose version &> /dev/null; then
    echo "❌ Error: docker compose не найден"
    exit 1
fi

# Запускаем rust-transcoder если не запущен
echo "��� Checking rust-transcoder container status..."
if ! docker compose ps rust-transcoder 2>/dev/null | grep -q "Up"; then
    echo "   Starting rust-transcoder..."
    docker compose up -d rust-transcoder
    sleep 3
fi

# Получаем container ID
CONTAINER_ID=$(docker compose ps -q rust-transcoder)
if [ -z "$CONTAINER_ID" ]; then
    echo "❌ Error: rust-transcoder container не найден"
    exit 1
fi

echo "✅ Container ID: $CONTAINER_ID"
echo ""

# Функция для получения memory usage в MB
get_memory_mb() {
    docker stats --no-stream --format "{{.MemUsage}}" $CONTAINER_ID | awk '{print $1}' | sed 's/MiB//'
}

# Baseline memory (без нагрузки)
echo "��� Phase 1: Baseline memory (no load)"
BASELINE_MEM=$(get_memory_mb)
echo "   Memory: ${BASELINE_MEM} MB"
sleep 2

# 10 concurrent streams (SC-002 requirement)
echo ""
echo "��� Phase 2: 10 concurrent streams (SC-002 test)"
for i in {1..10}; do
    curl -s -X POST http://localhost:8090/transcode \
      -H "Content-Type: application/json" \
      -d '{"source_url": "https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3", "format": "opus"}' > /dev/null &
done

sleep 3
TEN_MEM=$(get_memory_mb)
echo "   Memory with 10 concurrent streams: ${TEN_MEM} MB"
echo ""

wait
sleep 5

AFTER_MEM=$(get_memory_mb)
echo "   Memory after completion: ${AFTER_MEM} MB"
echo ""

# Проверка SC-002
if (( $(echo "$TEN_MEM < 256" | bc -l) )); then
    echo "✅ SC-002 PASSED: Memory ${TEN_MEM} MB < 256 MB"
else
    echo "❌ SC-002 FAILED: Memory ${TEN_MEM} MB >= 256 MB"
    exit 1
fi
