# 📊 Monitoring Stack — Quick Start

> Production-ready мониторинг для 24/7 TV Telegram Bot

---

## 🚀 Быстрый старт (5 минут)

### 1. Настройка Telegram бота

```bash
# 1. Создайте бота через @BotFather в Telegram
#    Получите bot_token

# 2. Получите Chat ID через @userinfobot или @getidsbot

# 3. Добавьте в .env:
echo "ALERTMANAGER_TELEGRAM_BOT_TOKEN=ваш_токен" >> .env
echo "ALERTMANAGER_TELEGRAM_CHAT_ID=ваш_chat_id" >> .env
```

### 2. Запуск мониторинга

```bash
# Запустить весь стек (основной + мониторинг)
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Проверить статус
docker compose -f docker-compose.monitoring.yml ps
```

### 3. Тестирование алертов

```bash
# Запустить тест
chmod +x scripts/test-telegram-alerts.sh
bash scripts/test-telegram-alerts.sh

# Выберите "4" для запуска всех тестов
```

### 4. Доступ к UI

- **Grafana:** http://localhost:3001 (admin / admin)
- **Prometheus:** http://localhost:9090
- **Alertmanager:** http://localhost:19093

---

## 📊 Доступные дашборды

### Backend Advanced
- HTTP метрики (rate, errors, latency p50/p95/p99)
- Database connection pool
- Process metrics (CPU, memory, FDs)
- Latency heatmap

### PostgreSQL Advanced
- Database status (up/down, connections, tx rate)
- Cache hit ratio
- Locks & Deadlocks
- Top 10 tables by activity

### System Advanced
- CPU usage (total, by core, load average)
- Memory usage (total, available, swap)
- Disk I/O (read/write ops, bytes)
- Network traffic & errors

---

## 🚨 Категории алертов

### 🔴 Critical (немедленное действие)
- `BackendDown`, `DatabaseDown`, `StreamerDown`
- `HighErrorRate` (>10%)
- `DiskSpaceCritical` (<10%)
- `MemoryExhausted` (>95%)

### ⚠️ Warning (требуется внимание)
- `HighLatency` (p95 > 1s)
- `ElevatedErrorRate` (5-10%)
- `DiskSpaceWarning` (<20%)
- `HighMemoryUsage` (>85%)

### 📊 Performance (деградация)
- `BackendResponseTimeDegraded` (p95 > 500ms)
- `DatabaseSlowQueries` (>1000ms)
- `DatabasePoolSaturated` (>80%)
- `PostgreSQLLowCacheHitRatio` (<90%)

### 🎯 Application (специфичные)
- `StreamQualityDegraded`
- `TelegramAPIRateLimited`
- `PlaylistEmpty`
- `TranscoderDown`

---

## 📚 Документация

- **Полная инструкция:** [docs/deployment/TELEGRAM_ALERTS_SETUP.md](../deployment/TELEGRAM_ALERTS_SETUP.md)
- **Roadmap:** [docs/development/refactoring-roadmap.md](../development/refactoring-roadmap.md)
- **Отчёт Phase 2.1:** [docs/REPORTS/PHASE_2.1_MONITORING_COMPLETE.md](PHASE_2.1_MONITORING_COMPLETE.md)

---

## 🔧 Команды управления

```bash
# Запуск только мониторинга
docker compose -f docker-compose.monitoring.yml up -d

# Остановка мониторинга
docker compose -f docker-compose.monitoring.yml down

# Перезапуск конкретного сервиса
docker compose -f docker-compose.monitoring.yml restart prometheus
docker compose -f docker-compose.monitoring.yml restart grafana
docker compose -f docker-compose.monitoring.yml restart alertmanager

# Просмотр логов
docker logs sattva-prometheus -f
docker logs sattva-grafana -f
docker logs sattva-alertmanager -f

# Проверка health
curl http://localhost:9090/-/healthy    # Prometheus
curl http://localhost:3001/api/health   # Grafana
curl http://localhost:19093/-/healthy   # Alertmanager
```

---

## 🧪 Troubleshooting

### Алерты не приходят в Telegram

```bash
# 1. Проверьте переменные
docker exec sattva-alertmanager env | grep ALERTMANAGER_TELEGRAM

# 2. Проверьте логи
docker logs sattva-alertmanager --tail 50

# 3. Тест напрямую через Telegram API
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<CHAT_ID>" \
  -d "text=Test"
```

### Grafana не показывает данные

```bash
# 1. Проверьте Prometheus targets
curl http://localhost:9090/api/v1/targets

# 2. Проверьте метрики
curl http://localhost:8000/metrics  # Backend
curl http://localhost:9187/metrics  # PostgreSQL
curl http://localhost:9100/metrics  # Node Exporter
```

### Prometheus не scrape метрики

```bash
# Перезагрузить конфигурацию
curl -X POST http://localhost:9090/-/reload

# Проверить конфигурацию
docker exec sattva-prometheus promtool check config /etc/prometheus/prometheus.yml
```

---

## 📝 Конфигурационные файлы

```
config/monitoring/
├── prometheus.yml              # Scrape targets & alerting config
├── alertmanager.yml            # Telegram integration & routing
├── rules/
│   ├── critical.yml            # Критические алерты
│   ├── warning.yml             # Предупреждения
│   ├── performance.yml         # Производительность
│   └── application.yml         # Специфичные алерты
└── grafana/
    ├── provisioning/           # Datasources & dashboards
    └── dashboards/
        ├── backend-advanced.json
        ├── postgres-advanced.json
        └── system-advanced.json
```

---

## 🎯 Метрики успеха

| Метрика | Цель | Статус |
|---------|------|--------|
| Дашборды | 8 | ✅ |
| Alert Rules | 50+ | ✅ |
| Telegram Integration | Работает | ✅ |
| Документация | Полная | ✅ |
| Тест-скрипт | Создан | ✅ |

---

**🎉 Production-ready мониторинг готов!**

Если возникли вопросы — см. полную документацию в [TELEGRAM_ALERTS_SETUP.md](../deployment/TELEGRAM_ALERTS_SETUP.md)
