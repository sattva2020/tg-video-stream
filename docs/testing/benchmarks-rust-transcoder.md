# Benchmark Tests Documentation

## Обзор

Benchmarks для проверки производительности rust-transcoder микросервиса согласно Spec 020.

## Тесты

### T056: Latency Benchmark

**Файл:** `rust-transcoder/tests/benchmark_latency_test.rs`

**Требование SC-001:** Latency старта транскодирования < 200ms

**Тесты:**
- `test_transcode_start_latency` - одиночный запрос
- `test_transcode_latency_multiple_formats` - латентность для opus/pcm/aac
- `test_transcode_latency_with_filters` - латентность с фильтрами
- `test_health_endpoint_latency` - /health endpoint (< 50ms)
- `test_metrics_endpoint_latency` - /metrics endpoint (< 100ms)
- `benchmark_sequential_requests` - 10 последовательных запросов
- `test_concurrent_requests_latency` - 5 параллельных запросов

**Запуск локально (Docker):**
```bash
docker compose build rust-transcoder
docker compose run --rm rust-transcoder cargo test --release --test benchmark_latency_test -- --nocapture
```

**Запуск на сервере:**
```bash
cd /opt/telegram/rust-transcoder
docker compose exec rust-transcoder cargo test --release --test benchmark_latency_test -- --nocapture
```

### T057: Memory Benchmark

**Файл:** `tests/benchmark_memory.sh`

**Требование SC-002:** Memory usage < 256MB при 10 concurrent streams

**Фазы теста:**
1. Baseline memory (no load)
2. Health check
3. Single transcode request
4. 5 concurrent streams
5. 10 concurrent streams ⭐ SC-002 test
6. Memory after completion

**Запуск:**
```bash
./tests/benchmark_memory.sh
```

**Требования:**
- Docker compose
- rust-transcoder запущен
- curl

### T058: Load Test

**Файл:** `tests/load_test_50_streams.sh`

**Требование SC-006:** Система обрабатывает 50 concurrent streams

**Метрики:**
- Success rate (должен быть 100%)
- Latency: Min, Max, Average, Median, P95, P99
- Throughput (requests/sec)
- Prometheus metrics verification

**Запуск:**
```bash
./tests/load_test_50_streams.sh
```

**Опционально с GNU parallel:**
```bash
# Установка parallel (если нужно)
sudo apt-get install parallel  # Ubuntu/Debian
brew install parallel          # macOS
```

## Запуск всех benchmarks

**Файл:** `tests/run_all_benchmarks.sh`

```bash
./tests/run_all_benchmarks.sh
```

Последовательно выполняет:
1. T056: Latency benchmark
2. T057: Memory benchmark
3. T058: Load test

## Ожидаемые результаты

### SC-001: Latency
- ✅ Transcode start latency: < 200ms
- ✅ Health endpoint: < 50ms
- ✅ Metrics endpoint: < 100ms

### SC-002: Memory
- ✅ 10 concurrent streams: < 256MB
- ✅ No memory leaks

### SC-006: Load Test
- ✅ 50 concurrent streams: 100% success rate
- ✅ Average latency: < 2000ms
- ✅ Success rate: >= 95%

## Troubleshooting

### rust-transcoder не запущен
```bash
docker compose up -d rust-transcoder
docker compose ps rust-transcoder
```

### Cargo не найден (локально)
Используйте Docker:
```bash
docker compose run --rm rust-transcoder cargo test --release --test benchmark_latency_test
```

### Тесты падают с timeout
Увеличьте timeout в скриптах или проверьте доступность test URL:
```bash
curl -I https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3
```

### Memory benchmark показывает высокое использование
Проверьте baseline memory и активные процессы:
```bash
docker stats rust-transcoder
docker compose logs rust-transcoder
```

## Результаты benchmarks

После выполнения всех тестов:
- Latency результаты выводятся в stdout
- Memory статистика в stdout
- Load test результаты: `/tmp/rust-transcoder-load-test/results.csv`

### Пример results.csv
```csv
id,status_code,duration_ms,time_total_s
1,200,145,0.145
2,200,158,0.158
3,200,167,0.167
...
```

## CI/CD Integration

Добавьте в GitHub Actions:

```yaml
- name: Run Benchmarks
  run: |
    chmod +x tests/run_all_benchmarks.sh
    ./tests/run_all_benchmarks.sh
```

## Spec 020 Completion

После успешного выполнения всех benchmarks:
- ✅ T056: Latency benchmark
- ✅ T057: Memory benchmark
- ✅ T058: Load test

**Spec 020 Status: 59/59 tasks (100%) complete** 🎉
