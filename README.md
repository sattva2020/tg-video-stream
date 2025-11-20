# Telegram 24/7 Video Streamer (TDLib-free, PyTgCalls)

Этот пакет позволяет запускать **круглосуточную трансляцию YouTube-плейлиста** в видеочате Telegram-группы **без GUI**. 
Используются: **Pyrogram + PyTgCalls + FFmpeg + yt-dlp**. Нагрузка минимальная: 2 vCPU / 2–4 ГБ RAM достаточно.

> ⚠️ Важно: для трансляции в видеочат требуется **пользовательская сессия** (не Bot API). Боты не могут присоединяться к видеочатам.
Поэтому вы авторизуете **пользовательский аккаунт** Telegram и получаете `SESSION_STRING` один раз.

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

## Быстрый старт (Docker Compose)
Запуск всего стека (Стример + Админка + БД):
```bash
docker-compose up -d --build
```
- **Frontend (Admin Panel)**: http://localhost:3000
- **Backend (API)**: http://localhost:8000

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
1. Зайдите на https://my.telegram.org → **API development tools**.
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

## Настройка окружения
Создайте файл `.env` (можно скопировать `.env.template`):
```
API_ID=123456
API_HASH=your_api_hash_here
SESSION_STRING=your_session_string_here
CHAT_ID=-1001234567890      # id супергруппы или @username (без @)
VIDEO_QUALITY=720p          # 1080p/720p/480p (влияет на параметры FFmpeg)
LOOP=1                      # 1=крутить по кругу; 0=один проход
```

**Где взять CHAT_ID?**
- Если есть публичный username: просто укажите, например `CHAT_ID=@mygroup`.
- Если приватная группа, можно «узнать id» через @userinfobot или небольшим скриптом Pyrogram.

## Плейлист
Файл `streamer/playlist.txt` — по одной ссылке на строку:
```
https://www.youtube.com/watch?v=abcd1234
https://www.youtube.com/watch?v=efgh5678
https://www.youtube.com/watch?v=ijkl9012
```
Можно вставить ссылку на **плейлист** — скрипт распакует его в список треков.

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
- Обновить плейлист: отредактируйте `streamer/playlist.txt` — сервис подхватит новый список на следующей итерации.
- Перезапуск: `sudo systemctl restart tg_video_streamer`.

## Журналы
```bash
journalctl -u tg_video_streamer -f -n 200
```

## Безопасность
- Храните `.env` (особенно `SESSION_STRING`) только на сервере.
- Ограничьте доступ к `/opt/tg_video_streamer` правами пользователя.

## Лицензия
MIT
