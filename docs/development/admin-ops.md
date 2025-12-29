# Admin Operations Guide

## 🔧 Local Development Setup


### ngrok и Vite: предотвращение конфликтов портов
```bash
# 1. Перед запуском убедитесь, что НЕТ других процессов Vite или ngrok!
netstat -ano | findstr :3000
netstat -ano | findstr :3001
tasklist | findstr ngrok
tasklist | findstr node

# 2. Если порт 3000 занят — определите PID процесса:
netstat -ano | findstr :3000
# Завершите процесс (замените <PID> на нужный):
taskkill /PID <PID> /F

# 3. Запускайте только ОДИН экземпляр Vite и ngrok!
cd frontend && npm run dev &
ngrok http --domain=isographical-shawnta-sortably.ngrok-free.dev 3000
```

#### Вариант: прогон через прод-frontend (nginx) для security headers
```bash
# Остановите dev Vite, если он запущен

# Соберите/запустите прод-фронт без бэкенда (он уже работает отдельно)
VITE_API_BASE_URL=http://localhost:8000 \
VITE_API_URL=http://localhost:8000 \
VITE_ENABLE_BASIC_LOGIN=false \
VITE_TELEGRAM_BOT_USERNAME=SattvaStreamerAuth_bot \
  docker compose -f docker-compose.yml up -d --no-deps frontend

# Пробросьте ngrok на порт 3000 (nginx фронта)
ngrok http --domain=isographical-shawnta-sortably.ngrok-free.dev 3000

# Проверка заголовков локально (должны быть HSTS, CSP, X-Frame-Options и др.)
curl -I http://localhost:3000
# Ожидаемый набор: CSP без unsafe-inline/eval, HSTS preload, X-Frame-Options DENY,
# X-Content-Type-Options nosniff, Referrer-Policy strict-origin-when-cross-origin,
# Permissions-Policy geolocation/microphone/camera=(), COOP same-origin,
# COEP require-corp, CORP same-origin, Server без версии (server_tokens off).
# Разрешённые внешние источники для CSP/COEP: challenges.cloudflare.com (Turnstile),
# cdnjs.cloudflare.com (Remixicon CSS/шрифты). При добавлении новых внешних ресурсов
# обязательно добавить их в CSP и убедиться, что они отдают CORS/CORP.
```
В этом режиме отвечает nginx из прод-образа (включены security-headers.conf и rate-limit.conf), поэтому securityheaders.com даст оценку A/A+.

⚠️ **ВАЖНО**: Никогда не запускайте несколько окон с Vite/ngrok одновременно — это приведёт к конфликту портов и ошибкам (например, появится Grafana или другой сервис вместо фронтенда).

- Vite по умолчанию: `localhost:3000`
- Если порт 3000 занят, Vite выберет 3001, 3002 и т.д.
- Проверяйте занятость портов перед запуском!

### Процессы и Мониторинг

**Проверка запущенных сервисов:**
```bash
# Frontend (Vite)
ps aux | grep vite
netstat -ano | findstr :3000

# Backend (FastAPI)
ps aux | grep uvicorn
netstat -ano | findstr :8000

# ngrok
ps aux | grep ngrok
curl -s http://localhost:4040/api/tunnels
```

**Рестарт сервисов:**
```bash
# Frontend
cd frontend && npm run dev &

# Backend (если нужен)
cd backend && uvicorn src.main:app --reload --port 8000 &

# ngrok
kill <ngrok_pid>
ngrok http --domain=isographical-shawnta-sortably.ngrok-free.dev 3000 &
```

This guide describes the administrative operations available for the Telegram Video Streamer.

## Stream Control

The Admin Dashboard provides controls to manage the streamer service directly.

### Actions
- **Start**: Starts the streamer service if it is stopped.
- **Stop**: Stops the streamer service.
- **Restart**: Restarts the streamer service. This is useful for applying configuration changes or recovering from errors.

### API Endpoints
- `POST /admin/stream/control`: Accepts JSON `{ "action": "start" | "stop" | "restart" }`.

## Monitoring

### Logs
Real-time logs from the streamer service are available in the "Logs" tab of the dashboard.
- **API**: `GET /admin/stream/logs?lines=100`

### Metrics
System resource usage (CPU and RAM) for the streamer container is visualized in the "Metrics" tab.
- **API**: `GET /admin/stream/metrics`
- **Source**: Redis (collected via `psutil` inside the streamer container).

## Playlist Management

The playlist determines the sequence of videos played by the streamer.
- **Location**: `playlist.txt` in the shared data volume.
- **Management**: Use the "Playlist" tab in the dashboard to add, remove, or reorder videos.
- **Format**: Simple text file with one URL per line.
- **API**:
  - `GET /admin/playlist`: Returns the current list.
  - `POST /admin/playlist`: Updates the list with a new array of URLs.

## Auto-Session Recovery

The system includes a mechanism to attempt recovery if the Telegram session expires or becomes invalid.
- **Trigger**: Automatic upon `SessionExpired` or `AuthKeyInvalid` exceptions.
- **Action**:
  1. Logs a critical alert.
  2. Writes a status file (`session_status`).
  3. Restarts the streamer process to attempt a fresh connection.
- **Note**: If the session is permanently revoked (e.g., user logged out all sessions), manual intervention (re-login) is required.

## Extended Configuration

### FFmpeg Arguments
You can inject custom FFmpeg arguments via the `FFMPEG_ARGS` environment variable.
- **Usage**: Add `FFMPEG_ARGS="-preset veryfast -tune zerolatency"` to your `.env` file.
- **Application**: These arguments are appended to the video encoding parameters.

## Security

All admin endpoints are protected and require authentication. Ensure your admin user has the appropriate roles/permissions.
