# Telegram 24/7 Video Streamer (TDLib-free, PyTgCalls)

![Backend Coverage](https://img.shields.io/badge/backend%20coverage-98.70%25-brightgreen?style=flat-square&logo=pytest)
![Backend Tests](https://img.shields.io/badge/backend%20tests-353%20passed-success?style=flat-square&logo=pytest)
![Integration Tests](https://img.shields.io/badge/integration%20tests-19%20passed-success?style=flat-square&logo=fastapi)
![Frontend Tests](https://img.shields.io/badge/frontend%20tests-289%20passed-success?style=flat-square&logo=vitest)
![E2E Tests](https://img.shields.io/badge/e2e%20tests-36%20specs-blue?style=flat-square&logo=playwright)
![CI/CD](https://img.shields.io/badge/ci%2Fcd-github%20actions-blue?style=flat-square)
[![CI](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Backend%20Coverage%20Monitoring/badge.svg)](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/backend-coverage.yml)

Этот пакет позволяет запускать **круглосуточную трансляцию YouTube-плейлиста**
в видеочате Telegram-группы **без GUI**.
Используются: **Pyrogram + PyTgCalls + FFmpeg + yt-dlp**.
Нагрузка минимальная: 2 vCPU / 2–4 ГБ RAM достаточно.

> ⚠️ Важно: для трансляции в видеочат требуется **пользовательская сессия**
> (не Bot API). Боты не могут присоединяться к видеочатам.
> Поэтому вы авторизуете **пользовательский аккаунт** Telegram и получаете
> `SESSION_STRING` один раз.

## Структура проекта

- `streamer/` - Скрипты стриминга (Pyrogram + PyTgCalls)
- `backend/` - API сервер (FastAPI)
- `frontend/` - Веб-интерфейс (React Admin Panel)

## Возможности

- Крутит **YouTube-плейлист** по кругу (файл `streamer/playlist.txt`).
- Стримит **видео+аудио** в видеочат Telegram (до 30 слотов видео; остальные — зрители).
- Автовосстановление при падении трека, логирование.
- Запуск как systemd-сервис: `tg_video_streamer`.
- **Web Admin Panel** для управления стримом.

## Безопасность

Проект реализует современные стандарты безопасности:
- **Nginx**: Security Headers, Rate Limiting, Connection Limits.
- **Backend**: Strict CORS, JWT Auth.
- **Audit**: Автоматические тесты безопасности.

Подробнее: [docs/SECURITY.md](docs/SECURITY.md)

## Быстрый старт (Docker Compose)

- Локальная разработка, полный стек с hot-reload (backend, frontend dev, db, redis, streamer, rust-transcoder, мониторинг):

```bash
docker compose -f docker-compose.local.yml up -d
```

- Порты локально: backend 8000, frontend 3000, redis 6379, postgres 5432, rust-transcoder 18090 (health: http://localhost:18090/health), alertmanager 19093.

- Полный docker-стек (стенд/CI; без hot-reload):

```bash
docker compose -f docker-compose.yml up -d
```

> На проде backend и streamer работают через systemd (см. ai-instructions/DEPLOYMENT_SYNC_RULE.md); docker-compose.yml нужен для стендов или полного docker-развёртывания.

- **Frontend (Admin Panel)**: <http://localhost:3000>
- **Backend (API)**: <http://localhost:8000>

## Проверка веб-лендинга

Лендинг доступен по `/` и использует адаптивный макет (280 px → 4K), системный
стек шрифтов и фон ZenScene. Для smoke-проверок используйте Playwright и
Lighthouse:

```bash
cd frontend
npx playwright test tests/e2e/landing/landing-responsive.spec.ts tests/e2e/landing/landing-accessibility.spec.ts
npm run test:lh
```

Playwright гарантирует отсутствие горизонтального скролла на 280 px и
клавиатурный путь до CTA ≤3 табов. Команда `npm run test:lh` собирает Vite,
поднимает `vite preview` и сохраняет отчёты Lighthouse в `.internal/lighthouse/`
(значения perf/TTI фиксируются для Phase 6).

## Минимальные требования (для ручной установки)

- Ubuntu 22.04 / 24.04
- 2 vCPU, 2–4 GB RAM, 20 GB SSD
- Установленный `ffmpeg`

## Установка (Ручная, только стример)

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip ffmpeg
sudo mkdir -p /opt/tg_video_streamer
sudo cp -r ./streamer/* /opt/tg_video_streamer/
cd /opt/tg_video_streamer
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## Получение API ID / API HASH

1. Зайдите на <https://my.telegram.org> → **API development tools**.
2. Создайте приложение и получите `api_id` и `api_hash`.

## Генерация SESSION_STRING

Один раз авторизуйтесь, чтобы получить строку сессии (хранится локально).

```bash
cd /opt/tg_video_streamer
source venv/bin/activate
python generate_session.py
```

Скрипт спросит: номер телефона, код из Telegram, пароль 2FA (если есть).
На выходе получите строку сессии — вставьте её в `.env` (см. ниже).

> **Примечание о двухфакторной аутентификации (2FA):**
> Если у вас включен Cloud Password в Telegram:
> 1. Введите номер телефона → получите код
> 2. Введите код → система запросит пароль 2FA
> 3. Введите пароль → получите SESSION_STRING
>
> Подробности об исправлении проблем с 2FA: [docs/bugfixes/TELEGRAM_2FA_FIX.md](docs/bugfixes/TELEGRAM_2FA_FIX.md)

## Настройка окружения

Создайте файл `.env` (можно скопировать `.env.template`):

```ini
API_ID=your_api_id
API_HASH=your_api_hash
# SESSION_STRING removed - authorization is handled via GUI
CHAT_ID=-1001234567890      # id супергруппы или @username (без @)
VIDEO_QUALITY=720p          # 1080p/720p/480p (влияет на параметры FFmpeg)
LOOP=1                      # 1=крутить по кругу; 0=один проход
```

**Где взять CHAT_ID?**

- Если есть публичный username: просто укажите, например `CHAT_ID=@mygroup`.
- Если приватная группа, можно «узнать id» через @userinfobot или небольшим
  скриптом Pyrogram.

## Плейлист

Файл `streamer/playlist.txt` — по одной ссылке на строку:

```text
https://www.youtube.com/watch?v=abcd1234
https://www.youtube.com/watch?v=efgh5678
https://www.youtube.com/watch?v=ijkl9012
```

Можно вставить ссылку на **плейлист** —
скрипт распакует его в список треков.

## Запуск как сервис

Установите systemd-юнит и включите автозапуск:

```bash
sudo cp streamer/tg_video_streamer.service /etc/systemd/system/tg_video_streamer.service
# Отредактируйте путь в сервисе, если нужно
sudo systemctl daemon-reload
sudo systemctl enable tg_video_streamer
sudo systemctl start tg_video_streamer
sudo systemctl status tg_video_streamer -l
```

## Управление

- Обновить плейлист: отредактируйте `streamer/playlist.txt` — сервис подхватит
  новый список на следующей итерации.
- Перезапуск: `sudo systemctl restart tg_video_streamer`.

## Журналы

```bash
journalctl -u tg_video_streamer -f -n 200
```

## Частая проблема: "Подключение" → выбрасывает из видеочата

Если аккаунт из `SESSION_STRING` при попытке войти/запустить видеочат пишет «соединение» и сразу вылетает, чаще всего причина одна из двух:

1) **Нет прав начинать видеочат** в группе (в настройках группы «Кто может начинать видеочаты» = только админы)
  - Решение: выдайте аккаунту-стримеру права администратора **или** запустите видеочат вручную админом и только затем запускайте стример.
  - Обходной путь (если видеочат запускаете вручную): установите `TG_CALL_AUTO_START=0`, чтобы стример не пытался сам создавать видеочат.

2) **Сетевой блок Telegram Calls (UDP/VoIP)**
  - Быстрая проверка: попробуйте обычный звонок Telegram 1-на-1.
  - Решение: другая сеть/мобильный интернет, VPN, проверка фаервола/провайдера.

## Безопасность

- Храните `.env` (особенно `SESSION_STRING`) только на сервере.
- Ограничьте доступ к `/opt/tg_video_streamer` правами пользователя.

## 🧪 Testing & Quality Assurance

### Backend Testing

Проект имеет **98.75% покрытие тестами** для 8 приоритетных сервисов:

| Сервис | Coverage | Tests | Status |
|--------|----------|-------|--------|
| session_service | 100% | 29 | ✅ |
| activity_service | 100% | 29 | ✅ |
| playback_service | 99% | 82 | ✅ |
| queue_service | 99% | 60 | ✅ |
| telegram_rate_limiter | 99% | 54 | ✅ |
| channel_service | 99% | 55 | ✅ |
| auth_service | 98% | 23 | ✅ |
| priority_queue_service | 96% | 46 | ✅ |

**Запуск тестов:**

```bash
cd backend

# Все приоритетные сервисы
pytest tests/test_playback_service.py tests/test_auth_service.py \
  tests/test_session_service.py tests/test_activity_service.py \
  tests/test_telegram_rate_limiter.py tests/test_queue_service.py \
  tests/test_priority_queue_service.py tests/test_channel_service.py \
  --cov=src.services --cov-report=term-missing --cov-branch -v

# Быстрый запуск
pytest -q

# С coverage отчётом
pytest --cov=src --cov-report=html
```

### CI/CD Integration

Coverage автоматически отслеживается в GitHub Actions:
- ✅ Проверка при каждом PR
- ✅ Автоматические отчёты в artifacts
- ✅ Threshold: минимум 95% для priority services
- ✅ Badge в README обновляется автоматически

Подробнее: [docs/testing/](docs/testing/) и `.github/workflows/backend-coverage.yml`

## Лицензия

MIT
