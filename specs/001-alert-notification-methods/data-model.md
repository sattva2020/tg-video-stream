# Модель данных

## Сущности

### NotificationChannel
- Поля: `id`, `name`, `type` (email/telegram/webhook/slack/teams/discord/pagerduty/opsgenie/pushover/sms), `config` (JSON: creds, endpoints), `enabled`, `status` (ok/error/testing), `test_at`, `concurrency_limit`, `retry_attempts`, `retry_interval_sec`, `timeout_sec`, `primary` (bool), `created_at`, `updated_at`.
- Валидации: уникальное `name`; обязательные поля в `config` по типу (SMTP host/port/user/pass, bot token/chat_id, webhook URL и метод); `retry_attempts` 1-5; `timeout_sec` 1-120.

### NotificationTemplate
- Поля: `id`, `name`, `locale` (ru/en), `subject` (nullable для non-email), `body`, `variables` (список допустимых макросов), `created_at`, `updated_at`.
- Валидации: обязательны `name`, `body`; `locale` в {ru,en}; длина subject ≤255.

### Recipient
- Поля: `id`, `type` (email/telegram/webhook/sms/etc.), `address` (email/URL/chat_id/phone), `status` (active/blocked/opt-out), `silence_windows` (cron/timeperiod spec), `created_at`, `updated_at`.
- Валидации: адрес по типу (email RFC, URL, digits для phone, int/str для chat_id); `status` из перечисления.

### NotificationRule
- Поля: `id`, `name`, `enabled`, `severity_filter` (set), `tag_filter` (ключ-значение/список), `host_filter`, `recipients` (many-to-many), `channels_order` (список channel_id с приоритетом), `failover_timeout_sec`, `silence_windows`, `rate_limit` (per recipient/channel), `dedup_window_sec`, `template_id`, `test_channel_ids` (для пробной отправки), `created_at`, `updated_at`.
- Валидации: `failover_timeout_sec` ≥0; `channels_order` не пуст; `dedup_window_sec` ≥0; `rate_limit` >=0; хотя бы один фильтр/правило маршрутизации задан.

### DeliveryLog
- Поля: `id`, `event_id` (внешний идентификатор события), `rule_id`, `channel_id`, `recipient_id`, `status` (success/fail/failover/suppressed/rate-limited/deduped), `attempt`, `latency_ms`, `response_code`, `response_body` (truncated), `error_message`, `created_at`.
- Валидации: `latency_ms` ≥0; `attempt` ≥1.

## Связи
- NotificationChannel 1..* DeliveryLog
- NotificationTemplate 1..* NotificationRule
- NotificationRule many-to-many Recipient (через связующую таблицу)
- NotificationRule references channels (ordered list, хранить как array или отдельная таблица `notification_rule_channels` с полем order)
- DeliveryLog ссылается на Rule/Channel/Recipient/Template (косвенно).

## Дополнительные правила
- Дедупликация: ключ = (event_id, rule_id, recipient_id) с TTL `dedup_window_sec` в Redis; логироваться как `deduped` без попытки отправки.
- Rate-limit: ключ = (recipient_id, channel_type) с окном, хранение счётчика в Redis; при превышении логируется `rate-limited`.
- Silence windows: проверяются до постановки в очередь; подавленные события логируются как `suppressed`.
