# Настройка Telegram Alerts для мониторинга

> **Создан:** 27 декабря 2025  
> **Назначение:** Инструкция по настройке Telegram бота для получения алертов от Prometheus Alertmanager

---

## 📋 Содержание

1. [Создание Telegram бота](#создание-telegram-бота)
2. [Получение Chat ID](#получение-chat-id)
3. [Конфигурация переменных](#конфигурация-переменных)
4. [Тестирование алертов](#тестирование-алертов)
5. [Типы алертов](#типы-алертов)
6. [Troubleshooting](#troubleshooting)

---

## 🤖 Создание Telegram бота

### Шаг 1: Создание бота через BotFather

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Введите имя бота: `Sattva Monitoring Bot` (или любое другое)
4. Введите username бота: `sattva_monitoring_bot` (должен заканчиваться на `_bot`)
5. **BotFather вернёт токен** вида: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### Шаг 2: Сохранение токена

⚠️ **ВАЖНО:** Никогда не коммитьте токен в Git!

Добавьте токен в `.env`:
```bash
ALERTMANAGER_TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

---

## 🆔 Получение Chat ID

### Вариант 1: Через @userinfobot

1. Найдите бота [@userinfobot](https://t.me/userinfobot)
2. Отправьте любое сообщение
3. Бот вернёт ваш User ID

### Вариант 2: Через @getidsbot

1. Найдите бота [@getidsbot](https://t.me/getidsbot)
2. Отправьте `/start`
3. Бот покажет ваш Chat ID

### Вариант 3: Через Telegram Web

1. Откройте [web.telegram.org](https://web.telegram.org)
2. Откройте чат с собой (Saved Messages)
3. URL будет содержать ваш ID: `https://web.telegram.org/a/#-1234567890`
4. Используйте число после `#` (без минуса для личных чатов)

### Для группового чата:

1. Добавьте вашего бота в группу
2. Отправьте в группу команду `/my_id` боту [@userinfobot](https://t.me/userinfobot)
3. Или используйте API метод `getUpdates`:

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates"
```

Найдите в JSON ответе поле `"chat":{"id":-1234567890}`

### Сохранение Chat ID

Добавьте в `.env`:
```bash
ALERTMANAGER_TELEGRAM_CHAT_ID=-1234567890
```

⚠️ **Для групп Chat ID отрицательный!**

---

## ⚙️ Конфигурация переменных

### 1. Основной `.env` файл

```bash
# Alerting (Alertmanager -> Telegram)
ALERTMANAGER_TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ALERTMANAGER_TELEGRAM_CHAT_ID=-1234567890
```

### 2. Проверка конфигурации Alertmanager

Файл: `config/monitoring/alertmanager.yml`

```yaml
receivers:
  - name: 'telegram-notifications'
    telegram_configs:
      - bot_token: '${ALERTMANAGER_TELEGRAM_BOT_TOKEN}'
        chat_id: ${ALERTMANAGER_TELEGRAM_CHAT_ID}
        api_url: 'https://api.telegram.org'
        parse_mode: 'HTML'
        send_resolved: true
```

### 3. Применение изменений

```bash
# Перезапуск мониторинга
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml restart alertmanager

# Проверка логов
docker logs sattva-alertmanager
```

---

## 🧪 Тестирование алертов

### Способ 1: Через Alertmanager API

Отправка тестового алерта:

```bash
curl -X POST http://localhost:19093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning",
      "instance": "test"
    },
    "annotations": {
      "summary": "This is a test alert",
      "description": "Testing Telegram integration"
    }
  }]'
```

### Способ 2: Через Prometheus (триггер реального алерта)

Временно измените порог в `config/monitoring/rules/critical.yml`:

```yaml
- alert: TestHighCPU
  expr: node_cpu_seconds_total > 0  # Всегда true
  for: 10s
  labels:
    severity: warning
  annotations:
    summary: "Test alert for Telegram"
    description: "This alert will fire immediately for testing"
```

Перезапустите Prometheus:

```bash
docker compose -f docker-compose.monitoring.yml restart prometheus
```

**Не забудьте удалить тестовый алерт после проверки!**

### Способ 3: Прямая отправка через Telegram API

```bash
BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
CHAT_ID="-1234567890"

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -H 'Content-Type: application/json' \
  -d "{
    \"chat_id\": \"${CHAT_ID}\",
    \"text\": \"🔔 Test alert from Prometheus\",
    \"parse_mode\": \"HTML\"
  }"
```

---

## 🚨 Типы алертов

### Critical (🔥 Критические)

**Немедленное действие требуется:**
- `StreamerDown` — Streamer сервис недоступен
- `BackendDown` — Backend API недоступен
- `DatabaseDown` — База данных недоступна
- `DiskSpaceCritical` — < 10% свободного места
- `MemoryExhausted` — > 95% памяти использовано

### Warning (⚠️ Предупреждения)

**Требуется внимание:**
- `HighLatency` — Высокая задержка API
- `ElevatedErrorRate` — 5-10% ошибок
- `DiskSpaceWarning` — < 20% свободного места
- `HighMemoryUsage` — > 85% памяти использовано

### Performance (📊 Производительность)

**Деградация производительности:**
- `BackendResponseTimeDegraded` — p95 latency > 500ms
- `DatabaseSlowQueries` — Медленные запросы
- `DatabasePoolSaturated` — > 80% connection pool

### Application (🎯 Приложение)

**Специфичные для приложения:**
- `StreamQualityDegraded` — Качество стрима упало
- `TelegramAPIRateLimited` — Rate limit от Telegram
- `PlaylistEmpty` — Пустой плейлист
- `TranscoderDown` — Rust transcoder недоступен

---

## 🔧 Troubleshooting

### Проблема: Алерты не приходят

#### Проверка 1: Токен и Chat ID

```bash
# Проверка переменных окружения в контейнере
docker exec sattva-alertmanager env | grep ALERTMANAGER_TELEGRAM

# Должны быть установлены:
# ALERTMANAGER_TELEGRAM_BOT_TOKEN=...
# ALERTMANAGER_TELEGRAM_CHAT_ID=...
```

#### Проверка 2: Конфигурация Alertmanager

```bash
# Проверка синтаксиса конфига
docker exec sattva-alertmanager amtool check-config /etc/alertmanager/alertmanager.yml

# Проверка текущей конфигурации
curl http://localhost:19093/api/v1/status
```

#### Проверка 3: Логи Alertmanager

```bash
docker logs sattva-alertmanager --tail 100 -f
```

Ищите ошибки:
- `Unauthorized` — неверный токен
- `Bad Request: chat not found` — неверный Chat ID
- `Connection refused` — нет доступа к api.telegram.org

#### Проверка 4: Тест отправки напрямую

```bash
BOT_TOKEN="ваш_токен"
CHAT_ID="ваш_chat_id"

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=Test message"
```

### Проблема: Бот не отвечает

1. **Проверьте, что бот запущен:**
   - Откройте чат с ботом в Telegram
   - Отправьте `/start`

2. **Для группового чата:**
   - Убедитесь, что бот добавлен в группу
   - Бот должен быть администратором (для некоторых типов групп)

3. **Проверьте Chat ID:**
   ```bash
   # Получить updates и найти правильный chat_id
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
   ```

### Проблема: Алерты дублируются

1. **Проверьте настройки группировки в `alertmanager.yml`:**
   ```yaml
   route:
     group_by: ['alertname', 'severity']
     group_wait: 30s
     group_interval: 5m
     repeat_interval: 4h
   ```

2. **Увеличьте `repeat_interval`** для менее частой отправки повторных алертов

### Проблема: Форматирование сообщений сломано

1. **Проверьте HTML разметку** в `alertmanager.yml`
2. **Escape спецсимволы HTML:** `<`, `>`, `&` должны быть экранированы
3. **Используйте `parse_mode: 'MarkdownV2'`** если предпочитаете Markdown

---

## 📚 Полезные ссылки

- [Prometheus Alerting Documentation](https://prometheus.io/docs/alerting/latest/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Telegram Bot API - sendMessage](https://core.telegram.org/bots/api#sendmessage)

---

## ✅ Checklist настройки

- [ ] Создан Telegram бот через @BotFather
- [ ] Получен `ALERTMANAGER_TELEGRAM_BOT_TOKEN`
- [ ] Получен `ALERTMANAGER_TELEGRAM_CHAT_ID`
- [ ] Переменные добавлены в `.env`
- [ ] Alertmanager перезапущен
- [ ] Отправлен тестовый алерт
- [ ] Алерт получен в Telegram
- [ ] Проверены логи Alertmanager (нет ошибок)
- [ ] Настроены inhibition rules (опционально)

---

**Готово!** Теперь вы будете получать алерты о состоянии системы в Telegram 🎉
