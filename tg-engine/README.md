# Sattva TG Engine - AyuGram Headless Build

Headless Telegram-движок на базе AyuGramDesktop для 24/7 видеостриминга.

## Описание

Этот сервис предоставляет нативный C++ движок Telegram на базе [AyuGramDesktop](https://github.com/AyuGram/AyuGramDesktop), который включает:
- **tgcalls** — официальная библиотека видеозвонков
- **WebRTC** — транспорт аудио/видео
- **MTProto** — протокол шифрования

## Деплой через Dokploy

### Шаг 1: Создание сервиса

1. Откройте Dokploy: `https://dokploy.sattva-ai.top/dashboard/projects`
2. Выберите проект `sattva-streamer` (если нет — создайте через **+ Create Project**)
3. **+ Add Service** → **Application** (не Compose!)
4. Имя: `tg-engine`

### Шаг 2: Настройка билда

1. **Source**: Git
2. **Repository**: `https://github.com/YOUR_REPO/telegram` (или локальный)
3. **Dockerfile Path**: `tg-engine/Dockerfile`

### Шаг 3: Environment Variables

```env
TDESKTOP_API_ID=37831214
TDESKTOP_API_HASH=1a10843db60c599ce2ec67bc6a55f1c2
```

### Шаг 4: Volumes

| Container Path | Host Path / Volume |
|----------------|-------------------|
| `/data/tg-session` | `tg-engine-session` |

### Шаг 5: Deploy

Нажмите **Deploy** и дождитесь сборки (30-60 минут).

## Локальная сборка

```bash
cd tg-engine

# Сборка образа
docker build \
  --build-arg TDESKTOP_API_ID=37831214 \
  --build-arg TDESKTOP_API_HASH=1a10843db60c599ce2ec67bc6a55f1c2 \
  -t sattva-tg-engine:latest .

# Запуск
docker run -d \
  --name tg-engine \
  -v tg-session:/data/tg-session \
  sattva-tg-engine:latest
```

## Структура

```
tg-engine/
├── Dockerfile          # Multi-stage build
├── README.md           # Эта документация
└── headless/           # [TODO] Headless модуль (Phase 2)
    ├── rpc_server.cpp
    └── call_controller.cpp
```

## Фазы разработки

- [x] Phase 1: Dockerfile для сборки AyuGram
- [ ] Phase 2: Headless режим (убрать Qt UI)
- [ ] Phase 3: JSON-RPC API
- [ ] Phase 4: Python client
- [ ] Phase 5: Интеграция со streamer

## Ссылки

- [AyuGramDesktop](https://github.com/AyuGram/AyuGramDesktop)
- [tgcalls](https://github.com/TelegramMessenger/tgcalls)
- [PyTgCalls](https://github.com/pytgcalls/pytgcalls)
