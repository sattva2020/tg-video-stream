#!/usr/bin/env bash
# Load Test: 50 concurrent streams
# Проверяет требование SC-006: система должна обрабатывать 50 concurrent streams
#
# Usage: ./tests/load_test_50_streams.sh

set -euo pipefail

echo "⚡ Load Test - 50 Concurrent Streams"
echo "==========================================="
echo ""

# Проверяем зависимости
if ! command -v curl &> /dev/null; then
    echo "❌ Error: curl не найден"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Error: docker не найден"
    exit 1
fi

# Проверяем что rust-transcoder запущен
echo "📦 Checking rust-transcoder status..."
if ! docker compose ps rust-transcoder 2>/dev/null | grep -q "Up"; then
    echo "   Starting rust-transcoder..."
    docker compose up -d rust-transcoder
    sleep 3
fi

# Проверяем health endpoint
echo "🏥 Health check..."
HEALTH_RESPONSE=$(curl -s http://localhost:8090/health)
if echo "$HEALTH_RESPONSE" | grep -q "\"status\":\"healthy\""; then
    echo "✅ rust-transcoder is healthy"
else
    echo "❌ rust-transcoder is not healthy"
    echo "$HEALTH_RESPONSE"
    exit 1
fi
echo ""

# Подготовка
CONCURRENT_STREAMS=50
SUCCESS_COUNT=0
FAILED_COUNT=0
TOTAL_TIME=0
TEMP_DIR="/tmp/rust-transcoder-load-test"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

echo "🚀 Starting load test with $CONCURRENT_STREAMS concurrent streams..."
echo "   Test URL: https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3"
echo "   Output format: opus"
echo "   Quality: medium"
echo ""

# Записываем начальное время
START_TIME=$(date +%s)

# Функция для одного transcode запроса
transcode_request() {
    local id=$1
    local start=$(date +%s%3N)
    
    local response=$(curl -s -w "\n%{http_code}\n%{time_total}" \
        -X POST http://localhost:8090/transcode \
        -H "Content-Type: application/json" \
        -d '{
            "source_url": "https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3",
            "format": "opus",
            "quality": "medium"
        }' 2>&1)
    
    local status_code=$(echo "$response" | tail -2 | head -1)
    local time_total=$(echo "$response" | tail -1)
    local end=$(date +%s%3N)
    local duration=$((end - start))
    
    # Сохраняем результат
    echo "$id,$status_code,$duration,$time_total" >> "$TEMP_DIR/results.csv"
    
    if [ "$status_code" = "200" ]; then
        echo "✅ Request $id: OK (${duration}ms)"
    else
        echo "❌ Request $id: FAILED (status: $status_code)"
    fi
}

# Экспорт функции для parallel
export -f transcode_request
export TEMP_DIR

# Запуск 50 параллельных запросов
echo "⏳ Executing $CONCURRENT_STREAMS parallel requests..."
echo ""

# Если есть GNU parallel, используем его
if command -v parallel &> /dev/null; then
    seq 1 $CONCURRENT_STREAMS | parallel -j $CONCURRENT_STREAMS transcode_request {}
else
    # Иначе используем background jobs
    for i in $(seq 1 $CONCURRENT_STREAMS); do
        transcode_request $i &
    done
    wait
fi

# Записываем конечное время
END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

echo ""
echo "⏱️  All requests completed in ${TOTAL_DURATION}s"
echo ""

# Анализ результатов
echo "==========================================="
echo "📊 Load Test Results Analysis"
echo "==========================================="

# Подсчёт успешных и failed requests
SUCCESS_COUNT=$(awk -F',' '$2 == 200 {count++} END {print count+0}' "$TEMP_DIR/results.csv")
FAILED_COUNT=$(awk -F',' '$2 != 200 {count++} END {print count+0}' "$TEMP_DIR/results.csv")
TOTAL_REQUESTS=$((SUCCESS_COUNT + FAILED_COUNT))

echo "Total requests:     $TOTAL_REQUESTS"
echo "Successful:         $SUCCESS_COUNT"
echo "Failed:             $FAILED_COUNT"
echo "Success rate:       $(echo "scale=2; $SUCCESS_COUNT * 100 / $TOTAL_REQUESTS" | bc)%"
echo ""

# Latency статистика
if [ $SUCCESS_COUNT -gt 0 ]; then
    echo "Latency statistics (successful requests):"
    
    # Min latency
    MIN_LATENCY=$(awk -F',' '$2 == 200 {print $3}' "$TEMP_DIR/results.csv" | sort -n | head -1)
    echo "  Min:     ${MIN_LATENCY} ms"
    
    # Max latency
    MAX_LATENCY=$(awk -F',' '$2 == 200 {print $3}' "$TEMP_DIR/results.csv" | sort -n | tail -1)
    echo "  Max:     ${MAX_LATENCY} ms"
    
    # Average latency
    AVG_LATENCY=$(awk -F',' '$2 == 200 {sum+=$3; count++} END {print int(sum/count)}' "$TEMP_DIR/results.csv")
    echo "  Average: ${AVG_LATENCY} ms"
    
    # Median latency
    MEDIAN_LATENCY=$(awk -F',' '$2 == 200 {print $3}' "$TEMP_DIR/results.csv" | sort -n | awk '{a[NR]=$1} END {print a[int(NR/2)]}')
    echo "  Median:  ${MEDIAN_LATENCY} ms"
    
    # P95 latency
    P95_LATENCY=$(awk -F',' '$2 == 200 {print $3}' "$TEMP_DIR/results.csv" | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.95)]}')
    echo "  P95:     ${P95_LATENCY} ms"
    
    # P99 latency
    P99_LATENCY=$(awk -F',' '$2 == 200 {print $3}' "$TEMP_DIR/results.csv" | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.99)]}')
    echo "  P99:     ${P99_LATENCY} ms"
fi

echo ""

# Throughput
THROUGHPUT=$(echo "scale=2; $SUCCESS_COUNT / $TOTAL_DURATION" | bc)
echo "Throughput:         ${THROUGHPUT} requests/sec"
echo ""

# Проверка метрик с Prometheus
echo "📈 Prometheus Metrics Check:"
METRICS=$(curl -s http://localhost:8090/metrics)

echo "Current metrics:"
echo "$METRICS" | grep "^transcode_requests_total" || echo "  transcode_requests_total: N/A"
echo "$METRICS" | grep "^transcode_active_streams" || echo "  transcode_active_streams: N/A"
echo "$METRICS" | grep "^transcode_errors_total" || echo "  transcode_errors_total: N/A"

echo ""
echo "==========================================="

# SC-006 Verification: все 50 requests должны быть успешными
if [ $SUCCESS_COUNT -eq $CONCURRENT_STREAMS ]; then
    echo "✅ SC-006 PASSED: All $CONCURRENT_STREAMS concurrent streams processed successfully"
    EXIT_CODE=0
else
    echo "❌ SC-006 FAILED: Only $SUCCESS_COUNT out of $CONCURRENT_STREAMS streams succeeded"
    EXIT_CODE=1
fi

# Дополнительные проверки
echo ""
echo "Additional checks:"

# Latency check (should be reasonable)
if [ $SUCCESS_COUNT -gt 0 ] && [ $AVG_LATENCY -lt 2000 ]; then
    echo "✅ Average latency ${AVG_LATENCY}ms is acceptable (< 2000ms)"
else
    echo "⚠️  Warning: Average latency ${AVG_LATENCY}ms is high"
fi

# Success rate check
SUCCESS_RATE=$(echo "scale=2; $SUCCESS_COUNT * 100 / $TOTAL_REQUESTS" | bc)
if (( $(echo "$SUCCESS_RATE >= 95" | bc -l) )); then
    echo "✅ Success rate ${SUCCESS_RATE}% is good (>= 95%)"
else
    echo "⚠️  Warning: Success rate ${SUCCESS_RATE}% is below 95%"
fi

echo ""
echo "==========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Load test completed successfully"
else
    echo "❌ Load test failed"
fi
echo "==========================================="
echo ""
echo "📁 Detailed results saved to: $TEMP_DIR/results.csv"

# Cleanup опционально
# rm -rf "$TEMP_DIR"

exit $EXIT_CODE
