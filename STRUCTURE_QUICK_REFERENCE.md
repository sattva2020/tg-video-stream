# Быстрая памятка по структуре

| Где класть файл? | Действие |
|------------------|----------|
| Корень репозитория | Только обязательные файлы: `README.md`, `docker-compose.yml`, `package.json`, `pyproject.toml`, инструкции верхнего уровня. Всё остальное перемещаем в профильные каталоги. |
| Временные/отладочные файлы | Кладём в `.internal/` или `_dev/`, добавляем в `.gitignore`, удаляем перед релизом. |
| Скрипты деплоя/утилиты | `scripts/`. Никаких одноразовых `.sh/.ps1` в корне. |
| Документация | `docs/` (русский язык, используем шаблоны). Инструкции для AI – `ai-instructions/`. |
| Backend код/тесты | `backend/src/…`, `backend/tests/…`. Миграции – `backend/alembic/`. |
| Frontend код/тесты | `frontend/src/…`, e2e – `frontend/tests/`. Паба – `frontend/public/`. |
| Streamer сервис | `streamer/` (никаких `.session` в git). |
| Конфигурации серверов | `config/` (systemd, monitoring, nginx и т.п.). После любой правки на сервере обновляем здесь. |
| Спецификации и планы | `specs/<номер>-<название>/`. Всегда добавляем README/прогресс. |
| Доп. тесты, smoke, песочницы | `tests/` c подпапками (`tests/smoke`, `tests/load` …). |

## Мини-чеклист перед коммитом
1. В корне нет `*_COMPLETE.md`, `test_*.sh`, лишних README.
2. `.env` не коммитим, используем `template.env` и `scripts/generate_env.sh`.
3. Документация обновлена + прогнаны `npm run docs:validate && npm run docs:report` (если менялись docs).
4. Логи/артефакты удалены или перенесены в `.internal/`.
5. Структура новых файлов описана в `PROJECT_STRUCTURE_GUIDELINES.md` при необходимости.

При сомнениях: сначала открыть `PROJECT_STRUCTURE_GUIDELINES.md`, затем свериться с этой памяткой.
