# 🚨 КРИТИЧЕСКИ ВАЖНО: Пути на сервере

## Два каталога — НЕ ПУТАТЬ!

### 1. `/opt/sattva-streamer/` — РЕПОЗИТОРИЙ (для разработки)
- Клон git репозитория
- Сюда делаются git pull
- **Здесь редактируется код**
- Файл: `multi_channel_runner.py` (в корне!)

### 2. `/opt/tg_video_streamer/current/streamer/` — ПРОДАКШН (запуск сервиса)
- Откуда реально запускается systemd сервис
- `current` — симлинк на release
- Файл: `multi_channel_runner.py` (в папке streamer/)
- **Сюда нужно КОПИРОВАТЬ изменения после редактирования!**

## Структура

```
/opt/
├── sattva-streamer/                    # 📁 GIT РЕПОЗИТОРИЙ
│   ├── multi_channel_runner.py         # ← РЕДАКТИРУЕМ ЗДЕСЬ
│   ├── sync-to-prod.sh                 # Скрипт синхронизации
│   ├── streamer/                       # Подпапка (не используется напрямую)
│   └── ...
│
└── tg_video_streamer/
    └── current/                        # Симлинк → releases/YYYYMMDDHHMMSS
        ├── venv/                       # Python venv
        └── streamer/                   # 📁 РАБОЧИЙ КАТАЛОГ СЕРВИСА
            ├── multi_channel_runner.py # ← КОПИРУЕМ СЮДА
            ├── redis_command_handler.py
            ├── utils.py
            └── ...
```

## Workflow изменения кода

### Шаг 1: Редактирование
```bash
nano /opt/sattva-streamer/multi_channel_runner.py
```

### Шаг 2: Синхронизация в продакшн
```bash
/opt/sattva-streamer/sync-to-prod.sh restart
```

Или вручную:
```bash
cp /opt/sattva-streamer/multi_channel_runner.py /opt/tg_video_streamer/current/streamer/
chown tgstream:tgstream /opt/tg_video_streamer/current/streamer/multi_channel_runner.py
rm -rf /opt/tg_video_streamer/current/streamer/__pycache__
systemctl restart tg_video_streamer
```

### Шаг 3: Проверка
```bash
journalctl -u tg_video_streamer --since '30 seconds ago' --no-pager
```

## Сервис systemd

```ini
# /etc/systemd/system/tg_video_streamer.service
WorkingDirectory=/opt/tg_video_streamer/current/streamer
ExecStart=/opt/tg_video_streamer/current/venv/bin/python multi_channel_runner.py
User=tgstream
```

## ⚠️ Частые ошибки

1. **Редактирование не применяется** — забыли скопировать в продакшн
2. **ModuleNotFoundError** — симлинки не работают (разные рабочие каталоги)
3. **Старый код выполняется** — забыли удалить `__pycache__`

## Быстрая команда (копировать полностью)

```bash
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 "/opt/sattva-streamer/sync-to-prod.sh restart"
```
