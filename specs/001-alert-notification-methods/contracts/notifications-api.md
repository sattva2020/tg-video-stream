# API Contracts: Notifications

Базовый префикс: `/api/notifications` (JSON, UTC timestamps, bearer auth).

## Channels
- `GET /channels` → 200 `[Channel]`.
- `POST /channels` → 201 `Channel` (body: `name`, `type`, `config`, `enabled`, `concurrency_limit`, `retry_attempts`, `retry_interval_sec`, `timeout_sec`).
- `PATCH /channels/{id}` → 200 `Channel`.
- `DELETE /channels/{id}` → 204.
- `POST /channels/{id}/test` → 202 `{status: queued, test_log_id}`.

`Channel.config` по типам (минимум):
- email: `smtp_host`, `smtp_port`, `use_tls`, `username`, `password`, `from_email`.
- telegram: `bot_token`, `chat_id`.
- webhook/slack/teams/discord: `url`, `method`, `headers`, `body_template`.
- pagerduty/opsgenie/pushover/sms: `url`/`token`/`api_key`/`phone` по протоколу провайдера.

## Templates
- `GET /templates` → 200 `[Template]`.
- `POST /templates` → 201 `Template` (body: `name`, `locale`, `subject?`, `body`, `variables`).
- `PATCH /templates/{id}` → 200 `Template`.
- `DELETE /templates/{id}` → 204.

## Recipients
- `GET /recipients` → 200 `[Recipient]`.
- `POST /recipients` → 201 `Recipient` (body: `type`, `address`, `status`, `silence_windows`).
- `PATCH /recipients/{id}` → 200 `Recipient`.
- `DELETE /recipients/{id}` → 204.

## Rules
- `GET /rules` → 200 `[Rule]`.
- `POST /rules` → 201 `Rule` (body: `name`, `enabled`, `severity_filter`, `tag_filter`, `host_filter`, `recipient_ids`, `channels_order`, `failover_timeout_sec`, `silence_windows`, `rate_limit`, `dedup_window_sec`, `template_id`).
- `PATCH /rules/{id}` → 200 `Rule`.
- `DELETE /rules/{id}` → 204.
- `POST /rules/{id}/test` → 202 `{status: queued, test_log_id}` (тестовая отправка по текущей маршрутизации).

## Logs
- `GET /logs` → 200 `[DeliveryLog]` (filters: `from`, `to`, `channel_id`, `recipient_id`, `status`, `event_id`).
- `GET /logs/{id}` → 200 `DeliveryLog`.

## Schemas (основные поля)
- `Channel`: `id`, `name`, `type`, `config`, `enabled`, `status`, `concurrency_limit`, `retry_attempts`, `retry_interval_sec`, `timeout_sec`, `test_at`, `created_at`, `updated_at`.
- `Template`: `id`, `name`, `locale`, `subject`, `body`, `variables`, `created_at`, `updated_at`.
- `Recipient`: `id`, `type`, `address`, `status`, `silence_windows`, `created_at`, `updated_at`.
- `Rule`: `id`, `name`, `enabled`, `severity_filter`, `tag_filter`, `host_filter`, `recipient_ids`, `channels_order`, `failover_timeout_sec`, `silence_windows`, `rate_limit`, `dedup_window_sec`, `template_id`, `created_at`, `updated_at`.
- `DeliveryLog`: `id`, `event_id`, `rule_id`, `channel_id`, `recipient_id`, `status`, `attempt`, `latency_ms`, `response_code`, `response_body`, `error_message`, `created_at`.

## Ответы об ошибках
- 400: `{"detail": "validation error"}`
- 401: `{"detail": "not authenticated"}`
- 404: `{"detail": "not found"}`
- 429: `{"detail": "rate limited"}`
