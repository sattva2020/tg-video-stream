# Prometheus Metrics Specification

**Source**: US-5 (Мониторинг)  
**Date**: 29.11.2025

---

## Backend Metrics

### HTTP Requests

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | method, path, status | Общее количество HTTP запросов |
| `http_request_duration_seconds` | Histogram | method, path | Длительность запросов |
| `http_requests_in_progress` | Gauge | method | Активные запросы |

**Example**:
```promql
# Requests per second by endpoint
rate(http_requests_total{path="/api/schedule"}[5m])

# p95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Database

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `db_connections_active` | Gauge | pool | Активные соединения в пуле |
| `db_connections_idle` | Gauge | pool | Свободные соединения |
| `db_query_duration_seconds` | Histogram | query_type | Длительность запросов |

### Application

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `app_info` | Gauge | version, env | Информация о приложении (всегда 1) |
| `app_startup_timestamp` | Gauge | - | Unix timestamp старта |

---

## Streamer Metrics

### Stream Status

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `stream_uptime_seconds` | Counter | channel_id | Время вещания |
| `stream_status` | Gauge | channel_id | 1=streaming, 0=stopped |
| `stream_viewers_current` | Gauge | channel_id | Текущие зрители |

### Buffer

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `buffer_size_bytes` | Gauge | type | Размер буфера (audio/video) |
| `buffer_underruns_total` | Counter | type | Количество buffer underruns |

### Errors

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `stream_errors_total` | Counter | error_type | Количество ошибок |
| `reconnect_attempts_total` | Counter | channel_id | Попытки переподключения |

**Example**:
```promql
# Error rate за 5 минут
rate(stream_errors_total[5m])

# Uptime percentage за час
sum(increase(stream_uptime_seconds[1h])) / 3600 * 100
```

---

## Alert Rules

### Critical Alerts

```yaml
# config/monitoring/rules/critical.yml
groups:
  - name: critical
    rules:
      - alert: StreamerDown
        expr: up{job="streamer"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Streamer is down"
          description: "Streamer has been down for more than 1 minute"

      - alert: DatabaseDown
        expr: up{job="backend"} == 0 or pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database is down"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"
```

### Warning Alerts

```yaml
# config/monitoring/rules/warning.yml
groups:
  - name: warning
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "p95 latency is {{ $value | humanizeDuration }}"

      - alert: BufferUnderruns
        expr: rate(buffer_underruns_total[5m]) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Buffer underruns detected"

      - alert: LowDiskSpace
        expr: node_filesystem_avail_bytes{mountpoint="/"} < 1e9
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Less than 1GB available on root filesystem"
```

---

## Grafana Dashboard Panels

### Streamer Overview Dashboard

| Panel | Type | Query | Description |
|-------|------|-------|-------------|
| Stream Status | Stat | `stream_status` | 1=🟢, 0=🔴 |
| Uptime | Stat | `sum(stream_uptime_seconds)` | Total streaming time |
| Error Rate | Gauge | `rate(stream_errors_total[5m])` | Errors per second |
| Buffer Health | Graph | `buffer_size_bytes` | Buffer over time |
| Viewers | Graph | `stream_viewers_current` | Viewers over time |

### Backend Overview Dashboard

| Panel | Type | Query | Description |
|-------|------|-------|-------------|
| Request Rate | Graph | `rate(http_requests_total[1m])` | RPS |
| Latency p95 | Graph | `histogram_quantile(0.95, ...)` | p95 latency |
| Error Rate | Stat | `rate(http_requests_total{status=~"5.."}[5m])` | 5xx rate |
| DB Connections | Gauge | `db_connections_active` | Active connections |

---

## Prometheus Configuration

```yaml
# config/monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/rules/*.yml'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'streamer'
    static_configs:
      - targets: ['streamer:9090']
    metrics_path: '/metrics'
```

---

## Alertmanager Configuration

```yaml
# config/monitoring/alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: 'telegram'
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        severity: critical
      receiver: 'telegram'
      repeat_interval: 1h

receivers:
  - name: 'telegram'
    telegram_configs:
      - bot_token: '${TELEGRAM_ALERT_BOT_TOKEN}'
        chat_id: ${TELEGRAM_ALERT_CHAT_ID}
        parse_mode: 'HTML'
        message: |
          🚨 <b>{{ .Status | toUpper }}</b>
          
          <b>Alert:</b> {{ .CommonLabels.alertname }}
          <b>Severity:</b> {{ .CommonLabels.severity }}
          
          {{ range .Alerts }}
          {{ .Annotations.summary }}
          {{ .Annotations.description }}
          {{ end }}
```

---

## Required Environment Variables (template.env)

```env
# Monitoring
GRAFANA_ADMIN_PASSWORD=change_this_secure_password_grafana
TELEGRAM_ALERT_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALERT_CHAT_ID=your_chat_id_here
```
