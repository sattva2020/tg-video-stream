#!/usr/bin/env bash
# Benchmark: Memory usage при 10 concurrent streams
# Проверяет требование SC-002: память должна быть < 256MB при 10 concurrent streams
#
# Usage: ./tests/benchmark_memory.sh

set -euo pipefail

echo "🔍 Memory Usage Benchmark - Rust Transcoder"
echo "==========================================="
echo ""

# Проверяем что docker compose доступен
if ! command -v docker &> /dev/null; then
    echo "❌ Error: docker не найден"
    exit 1
fi

# Проверяем что docker compose доступен
if ! docker compose version &> /dev/null; then
    echo "❌ Error: docker compose не найден"
    exit 1
fi

# Запускаем rust-transcoder если не запущен
echo "📦 Checking rust-transcoder container status..."
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
echo "📊 Phase 1: Baseline memory (no load)"
BASELINE_MEM=$(get_memory_mb)
echo "   Memory: ${BASELINE_MEM} MB"
sleep 2

# Проверяем health endpoint
echo ""
echo "📊 Phase 2: Health check"
curl -s http://localhost:8090/health > /dev/null
HEALTH_MEM=$(get_memory_mb)
echo "   Memory after health check: ${HEALTH_MEM} MB"
sleep 2

# Одиночный transcode request
echo ""
echo "📊 Phase 3: Single transcode request"
curl -s -X POST http://localhost:8090/transcode \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3",
    "format": "opus",
    "quality": "medium"
  }' > /dev/null &

sleep 1
SINGLE_MEM=$(get_memory_mb)
echo "   Memory with 1 stream: ${SINGLE_MEM} MB"
wait
sleep 2

# 5 concurrent streams
echo ""
echo "📊 Phase 4: 5 concurrent streams"
for i in {1..5}; do
    curl -s -X POST http://localhost:8090/transcode \
      -H "Content-Type: application/json" \
      -d '{
        "source_url": "https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3",
        "format": "opus"
      }' > /dev/null &
done

sleep 2
FIVE_MEM=$(get_memory_mb)
echo "   Memory with 5 concurrent streams: ${FIVE_MEM} MB"
wait
sleep 3

# 10 concurrent streams (SC-002 requirement)
echo ""
echo "📊 Phase 5: 10 concurrent streams (SC-002 test)"
for i in {1..10}; do
    curl -s -X POST http://localhost:8090/transcode \
      -H "Content-Type: application/json" \
      -d '{
        "source_url": "https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3",
        "format": "opus",
        "quality": "medium"
      }' > /dev/null &
done

sleep 3
TEN_MEM=$(get_memory_mb)
echo "   Memory with 10 concurrent streams: ${TEN_MEM} MB"
echo ""

# Ждём завершения всех запросов
echo "⏳ Waiting for all streams to complete..."
wait
sleep 5

# Проверяем память после завершения
AFTER_MEM=$(get_memory_mb)
echo "   Memory after streams completed: ${AFTER_MEM} MB"
echo ""

# Итоговая статистика
echo "==========================================="
echo "📈 Memory Usage Summary:"
echo "==========================================="
echo "Baseline (no load):          ${BASELINE_MEM} MB"
echo "After health check:          ${HEALTH_MEM} MB"
echo "1 concurrent stream:         ${SINGLE_MEM} MB"
echo "5 concurrent streams:        ${FIVE_MEM} MB"
echo "10 concurrent streams:       ${TEN_MEM} MB  ⭐ SC-002 TEST"
echo "After completion:            ${AFTER_MEM} MB"
echo ""

# Проверка SC-002: < 256MB при 10 concurrent streams
if (( $(echo "$TEN_MEM < 256" | bc -l) )); then
    echo "✅ SC-002 PASSED: Memory usage ${TEN_MEM} MB < 256 MB"
else
    echo "❌ SC-002 FAILED: Memory usage ${TEN_MEM} MB >= 256 MB"
    exit 1
fi

# Дополнительные проверки
echo ""
echo "Additional checks:"

# Memory leak check
MEM_DIFF=$(echo "$AFTER_MEM - $BASELINE_MEM" | bc)
echo "Memory increase after test: ${MEM_DIFF} MB"
if (( $(echo "$MEM_DIFF < 50" | bc -l) )); then
    echo "✅ No significant memory leak detected"
else
    echo "⚠️  Warning: Memory increased by ${MEM_DIFF} MB"
fi

# Peak memory
PEAK_MEM=$TEN_MEM
echo "Peak memory usage: ${PEAK_MEM} MB"

echo ""
echo "==========================================="
echo "✅ Memory benchmark completed successfully"
echo "==========================================="
