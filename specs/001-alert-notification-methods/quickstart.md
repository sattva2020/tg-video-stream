# Quickstart по фиче оповещений

1) Подготовить окружение
- Убедиться, что backend env собран (`python3.12`, Poetry/pip по проекту), запущены PostgreSQL+Redis (можно `docker-compose up -d backend db redis` из корня).
- Применить миграции: `cd backend && poetry run alembic upgrade head` (или `pip install -r requirements.txt` + alembic из pyproject).

2) Запуск сервисов оповещений
- Celery worker: `cd backend && poetry run celery -A src.worker.app worker -Q notifications -l info`.
- FastAPI backend: `cd backend && poetry run uvicorn src.run:app --reload` (или через docker-compose).

3) Создать базовые каналы и шаблоны (через API)
- Email: SMTP host/port/user/pass + from, test отправка.
- Telegram: bot token + chat_id, test отправка.
- Webhook: URL + метод/заголовки/тело, test отправка.

4) Настроить правило маршрутизации
- Severity/tags/hosts фильтр, список получателей, порядок каналов, таймаут failover, окно тишины, dedup/rate-limit.
- Привязать шаблон (RU/EN) и проверить «Отправить пробное сообщение».

5) Проверка
- Сгенерировать событие (через тестовый endpoint или фиктивный event) и убедиться в доставке/логах `DeliveryLog` (success/fail/failover/dedup/rate-limited).
- Проверить журнал фильтрацией по дате/каналу/получателю.

6) Тесты
- Backend: `cd backend && poetry run pytest -k notification` (или аналог в pip env).
- Frontend (если затрагивается UI настройки оповещений): `cd frontend && npm run test` и целевые e2e сценарии Playwright.
