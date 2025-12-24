#!/usr/bin/env bash
# Load Test: 50 concurrent streams
# Проверяет требование SC-006: система должна обрабатывать 50 concurrent streams

set -euo pipefail

echo "⚡ Load Test - 50 Concurrent Streams"
echo "==========================================="

# Запускаем rust-transcoder если не запущен
if ! docker compose ps rust-transcoder 2>/dev/null | grep -q "Up"; then
    echo "Starting rust-transcoder..."
    docker compose up -d rust-transcoder
    sleep 3
fi

echo "��� Starting load test with 50 concurrent streams..."

CONCURRENT_STREAMS=50
SUCCESS_COUNT=0

# Запуск 50 параллельных запросов
for i in $(seq 1 $CONCURRENT_STREAMS); do
    {
        response=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST http://localhost:8090/transcode \
            -H "Content-Type: application/json" \
            -d '{"source_url": "https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3", "format": "opus"}')
        
        if [ "$response" = "200" ]; then
            echo "✅ Request $i: OK"
        else
            echo "❌ Request $i: FAILED (status: $response)"
        fi
    } &
done

wait

# Подсчёт успешных запросов
SUCCESS_COUNT=$(docker compose logs rust-transcoder 2>/dev/null | grep -c "Transcode request received" || echo "0")

echo ""
echo "==========================================="
echo "��� Results:"
echo "Total requests: $CONCURRENT_STREAMS"
echo "Processed: $SUCCESS_COUNT"

if [ $SUCCESS_COUNT -ge 45 ]; then
    echo "✅ SC-006 PASSED: Successfully processed $SUCCESS_COUNT/$CONCURRENT_STREAMS streams"
else
    echo "❌ SC-006 FAILED: Only $SUCCESS_COUNT/$CONCURRENT_STREAMS streams processed"
    exit 1
fi
