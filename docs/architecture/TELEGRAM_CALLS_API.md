# Telegram Calls API — Техническая документация

> **Дата создания:** 21 декабря 2025  
> **Версия:** 1.0  
> **Статус:** Актуально

## Содержание

1. [Обзор архитектуры](#обзор-архитектуры)
2. [Стек технологий](#стек-технологий)
3. [End-to-End шифрование](#end-to-end-шифрование)
4. [Group Calls API](#group-calls-api)
5. [PyTgCalls — Python библиотека](#pytgcalls--python-библиотека)
6. [Типы звонков](#типы-звонков)
7. [WebRTC интеграция](#webrtc-интеграция)
8. [Практические примеры](#практические-примеры)
9. [Ссылки на документацию](#ссылки-на-документацию)

---

## Обзор архитектуры

### Официальные библиотеки Telegram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Telegram Calls Stack                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Bot API    │    │   TDLib     │    │ MTProto API │         │
│  │  (Боты)     │    │ (Клиенты)   │    │  (Низкий)   │         │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              tgcalls (C++ библиотека)                    │   │
│  │   github.com/TelegramMessenger/tgcalls                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     WebRTC                               │   │
│  │            (Аудио/Видео транспорт)                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Python обёртки

```
┌─────────────────────────────────────────────────────────────────┐
│                    Python Calls Stack                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  PyTgCalls (Python)                      │   │
│  │          github.com/pytgcalls/pytgcalls                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                NTgCalls (Cython binding)                 │   │
│  │          github.com/pytgcalls/ntgcalls                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              tgcalls (C++ библиотека)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────┬───────────┼───────────┬─────────────┐         │
│  │             │           │           │             │         │
│  ▼             ▼           ▼           ▼             ▼         │
│ Pyrogram   Telethon   Hydrogram      MTProto       FFmpeg      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Стек технологий

### Официальный стек Telegram

| Компонент | Описание | Репозиторий |
|-----------|----------|-------------|
| **tgcalls** | C++ библиотека для звонков | [TelegramMessenger/tgcalls](https://github.com/TelegramMessenger/tgcalls) |
| **WebRTC** | Транспорт аудио/видео | libwebrtc от Google |
| **MTProto 2.0** | Протокол шифрования | [core.telegram.org/mtproto](https://core.telegram.org/mtproto) |

### Python стек (используется в проекте)

| Компонент | Версия | Описание |
|-----------|--------|----------|
| **PyTgCalls** | 2.2.x | Python обёртка для звонков |
| **NTgCalls** | 2.0.x | Cython биндинг к tgcalls |
| **Pyrogram** | 2.0.x | MTProto клиент |
| **FFmpeg** | 6.x | Медиа-обработка |

---

## End-to-End шифрование

> Источник: [core.telegram.org/api/end-to-end/video-calls](https://core.telegram.org/api/end-to-end/video-calls)

### Протокол обмена ключами (Diffie-Hellman)

```
┌────────────────────────────────────────────────────────────────┐
│              Протокол создания звонка (E2E)                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Caller (A)                Server (S)               Callee (B) │
│      │                        │                        │       │
│      │ 1. getDhConfig()       │                        │       │
│      │ ──────────────────────>│                        │       │
│      │ <── p, g (2048-bit)    │                        │       │
│      │                        │                        │       │
│      │ 2. Генерирует a        │                        │       │
│      │    g_a = g^a mod p     │                        │       │
│      │    g_a_hash = SHA256(g_a)                       │       │
│      │                        │                        │       │
│      │ 3. requestCall(g_a_hash)                        │       │
│      │ ──────────────────────>│                        │       │
│      │                        │ updatePhoneCall        │       │
│      │                        │ ──────────────────────>│       │
│      │                        │ (phoneCallRequested)   │       │
│      │                        │                        │       │
│      │                        │ 4. B генерирует b      │       │
│      │                        │    g_b = g^b mod p     │       │
│      │                        │                        │       │
│      │                        │ acceptCall(g_b)        │       │
│      │                        │ <──────────────────────│       │
│      │                        │                        │       │
│      │ updatePhoneCall        │                        │       │
│      │ (phoneCallAccepted)    │                        │       │
│      │ <──────────────────────│                        │       │
│      │                        │                        │       │
│      │ 5. A вычисляет:        │                        │       │
│      │    key = g_b^a mod p   │                        │       │
│      │    fingerprint = SHA1(key)[0:8]                 │       │
│      │                        │                        │       │
│      │ confirmCall(g_a, fingerprint)                   │       │
│      │ ──────────────────────>│                        │       │
│      │                        │ updatePhoneCall        │       │
│      │                        │ ──────────────────────>│       │
│      │                        │ (phoneCall + g_a)      │       │
│      │                        │                        │       │
│      │                        │ 6. B проверяет:        │       │
│      │                        │    SHA256(g_a) == g_a_hash     │
│      │                        │    key = g_a^b mod p   │       │
│      │                        │    fingerprint match   │       │
│      │                        │                        │       │
│      └────────────── 256-byte shared key ──────────────┘       │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Шифрование данных звонка

```python
# Алгоритм шифрования пакетов (MTProto 2.0 optimized)

# 1. Вычисление msg_key
msg_key_large = SHA256(key[88+x:88+x+32] + decrypted_body)
msg_key = msg_key_large[8:24]  # 16 bytes

# 2. Вычисление AES ключа и IV
sha256_a = SHA256(msg_key + key[x:x+36])
sha256_b = SHA256(key[40+x:40+x+36] + msg_key)

aes_key = sha256_a[0:8] + sha256_b[8:24] + sha256_a[24:32]  # 32 bytes
aes_iv = sha256_b[0:4] + sha256_a[8:16] + sha256_b[24:28]   # 16 bytes

# 3. Шифрование
encrypted_body = AES_CTR(decrypted_body, aes_key, aes_iv)
packet = msg_key + encrypted_body

# x зависит от направления и типа соединения:
# x = 0   для outgoing + transport
# x = 8   для incoming + transport
# x = 128 для outgoing + signaling
# x = 136 для incoming + signaling
```

### Верификация ключа (Emoji)

Для защиты от MITM-атак используется визуальная верификация:

```python
# Генерация 4 эмодзи для верификации
key_visual = SHA256(key + g_a)  # g_a от Caller

# Разбиваем на 4 x 64-bit числа
emoji_indices = [
    (key_visual[i*8:(i+1)*8] as uint64) % 333
    for i in range(4)
]

# 333 возможных эмодзи → вероятность угадать: 1/333^4 ≈ 0.0000000001
```

---

## Group Calls API

### MTProto методы

| Метод | Описание |
|-------|----------|
| `phone.createGroupCall` | Создание группового звонка / видеочата |
| `phone.joinGroupCall` | Присоединение к звонку |
| `phone.leaveGroupCall` | Выход из звонка |
| `phone.discardGroupCall` | Завершение звонка (админ) |
| `phone.editGroupCallTitle` | Изменение названия |
| `phone.toggleGroupCallRecord` | Запись звонка |

### phone.createGroupCall

```
phone.createGroupCall#48cdc6d8 flags:#
  rtmp_stream:flags.2?true        // Включить RTMP стриминг
  peer:InputPeer                  // Канал/группа
  random_id:int                   // Уникальный ID клиента
  title:flags.0?string            // Название звонка
  schedule_date:flags.1?int       // Запланированный старт
  = Updates;
```

**Возможные ошибки:**
- `CHAT_ADMIN_REQUIRED` — Требуются права админа
- `CREATE_CALL_FAILED` — Ошибка создания
- `GROUPCALL_ALREADY_DISCARDED` — Звонок уже завершён

### phone.joinGroupCall

```
phone.joinGroupCall#8fb53057 flags:#
  muted:flags.0?true              // Замьючен при входе
  video_stopped:flags.2?true      // Видео выключено при входе
  call:InputGroupCall             // ID звонка
  join_as:InputPeer               // От чьего имени (канал/юзер)
  invite_hash:flags.1?string      // Хэш приглашения
  params:DataJSON                 // WebRTC параметры
  = Updates;
```

**Возможные ошибки:**
- `GROUPCALL_FORBIDDEN` — Звонок завершён
- `GROUPCALL_INVALID` — Неверный ID звонка
- `JOIN_AS_PEER_INVALID` — Нельзя войти от этого peer

---

## PyTgCalls — Python библиотека

### Архитектура PyTgCalls

```
┌─────────────────────────────────────────────────────────────────┐
│                      PyTgCalls v2.x                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    PyTgCalls (Main)                        │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │                    Methods                           │  │ │
│  │  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │  │ │
│  │  │  │  Calls  │ │Decorators│ │ Internal │ │ Stream  │  │  │ │
│  │  │  │         │ │          │ │          │ │ Methods │  │  │ │
│  │  │  │ leave   │ │ on_update│ │ connect  │ │ play    │  │  │ │
│  │  │  │ calls   │ │ on_end   │ │ handle   │ │ pause   │  │  │ │
│  │  │  │ ping    │ │          │ │          │ │ resume  │  │  │ │
│  │  │  └─────────┘ └──────────┘ └──────────┘ └─────────┘  │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                   NTgCalls (Binding)                       │ │
│  │              Cython → C++ tgcalls                          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                  MTProto Client                            │ │
│  │     Pyrogram / Telethon / Hydrogram                        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Типы и классы

#### MediaStream

```python
from pytgcalls.types import MediaStream, AudioQuality, VideoQuality

class MediaStream(Stream):
    class Flags(Flag):
        AUTO_DETECT = auto()  # Автоопределение типа
        REQUIRED = auto()     # Обязательный поток
        IGNORE = auto()       # Игнорировать поток

    def __init__(
        self,
        media_path: Union[str, Path, InputDevice, ExternalMedia],
        audio_parameters: AudioQuality = AudioQuality.HIGH,
        video_parameters: VideoQuality = VideoQuality.HD_720p,
        audio_path: Optional[str] = None,       # Отдельный путь к аудио
        audio_flags: Flags = Flags.AUTO_DETECT,
        video_flags: Flags = Flags.AUTO_DETECT,
        headers: Optional[Dict] = None,         # HTTP заголовки
        ffmpeg_parameters: Optional[str] = None,
        ytdlp_parameters: Optional[str] = None,
    ):
        pass
```

#### AudioQuality

```python
class AudioQuality(Enum):
    STUDIO = (96000, 2)  # 96kHz stereo
    HIGH = (48000, 2)    # 48kHz stereo (default)
    MEDIUM = (36000, 1)  # 36kHz mono
    LOW = (24000, 1)     # 24kHz mono
```

#### VideoQuality

```python
class VideoQuality(Enum):
    UHD_4K = (3840, 2160, 60)   # 4K 60fps
    QHD_2K = (2560, 1440, 60)   # 2K 60fps
    FHD_1080p = (1920, 1080, 60) # Full HD 60fps
    HD_720p = (1280, 720, 30)   # HD 30fps (default)
    SD_480p = (854, 480, 30)    # SD 30fps
    SD_360p = (640, 360, 30)    # SD 30fps
```

#### GroupCallConfig

```python
class GroupCallConfig:
    def __init__(
        self,
        invite_hash: Optional[str] = None,  # Для приватных чатов
        join_as: Any = None,                # От чьего имени
        auto_start: bool = True,            # Автосоздание звонка
    ):
        pass
```

### Метод play()

```python
async def play(
    self,
    chat_id: Union[int, str],
    stream: Optional[Union[str, Path, InputDevice, Stream]] = None,
    config: Optional[Union[CallConfig, GroupCallConfig]] = None,
):
    """
    Воспроизведение медиа в звонке.
    
    Алгоритм:
    1. Если stream = str/Path → автоматически создаёт MediaStream(stream)
    2. Вызывает stream.check_stream() для подготовки FFmpeg команд
    3. Если уже в звонке → обновляет источник потока
    4. Если нет звонка и auto_start=True → создаёт звонок
    5. Подключается к звонку через _connect_call()
    """
```

### check_stream() — логика определения типа

```python
async def check_stream(self):
    """
    Проверка и подготовка медиа-потока.
    
    Для видео:
    1. ffprobe анализирует файл
    2. Если codec_name in ['png', 'jpeg', 'jpg', 'mjpeg']:
       → ImageSourceFound → добавляет -loop 1 -framerate 1
    3. Если нет видео-дорожки и video_flags != REQUIRED:
       → camera = None → ГОЛОСОВОЙ ЧАТ
    
    Для аудио:
    1. Если audio_path не задан → берётся из media_path
    2. ffprobe проверяет аудио-дорожку
    3. Если нет аудио и audio_flags != REQUIRED:
       → microphone = None
    """
```

---

## Типы звонков

### Сравнение типов

| Тип | MediaStream | Результат |
|-----|-------------|-----------|
| Видеофайл (.mkv, .mp4) | `'video.mkv'` | Видеочат с видео |
| Изображение + аудио | `MediaStream('image.png', audio_path='audio.mp3')` | Видеочат со статикой |
| Только аудио | `'audio.mp3'` | **Голосовой чат** |
| Аудио + video_flags=IGNORE | `MediaStream('audio.mp3', video_flags=IGNORE)` | Голосовой чат |

### Как получить Видеочат с аудиофайлом

```python
# Правильный способ — изображение + audio_path
media = MediaStream(
    'placeholder.png',           # Изображение (автоматически -loop 1)
    audio_path='music.mp3',      # Аудиофайл
    audio_parameters=AudioQuality.HIGH,
    video_parameters=VideoQuality.HD_720p,
)

await pytg.play(chat_id, media, config=GroupCallConfig(auto_start=True))
```

### Алгоритм определения типа звонка

```
                    ┌─────────────────────┐
                    │   MediaStream()     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  check_stream()     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
    ┌─────────▼─────────┐             ┌─────────▼─────────┐
    │  Есть видео?      │             │  video_flags=     │
    │  (ffprobe)        │             │  IGNORE?          │
    └─────────┬─────────┘             └─────────┬─────────┘
              │                                 │
         ┌────┴────┐                       ┌────┴────┐
         │ YES     │ NO                    │ YES     │ NO
         ▼         ▼                       ▼         │
    ┌─────────┐  ┌─────────┐         ┌─────────┐    │
    │Изобра-  │  │camera=  │         │camera=  │    │
    │жение?   │  │None     │         │None     │    │
    └────┬────┘  └────┬────┘         └────┬────┘    │
         │            │                   │         │
    YES  │  NO        │                   │         │
         ▼  ▼         ▼                   ▼         ▼
    ┌─────────┐  ┌─────────┐         ┌─────────────────┐
    │-loop 1  │  │ Видео   │         │  Голосовой чат  │
    │-framerate 1│ │ поток  │         │  (без видео)    │
    └────┬────┘  └────┬────┘         └─────────────────┘
         │            │
         └─────┬──────┘
               ▼
      ┌─────────────────┐
      │   Видеочат      │
      │  (с видео)      │
      └─────────────────┘
```

---

## WebRTC интеграция

### Telegram Reflector сервера

Telegram использует собственные relay-сервера (reflectors) для NAT traversal:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Telegram Reflectors                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         ┌─────────────┐         ┌───────────┐ │
│  │   Client A  │◄───────►│  Reflector  │◄───────►│  Client B │ │
│  └─────────────┘         │   Server    │         └───────────┘ │
│        │                 └─────────────┘                │       │
│        │                                                │       │
│        │         ┌─────────────────────────────┐        │       │
│        └────────►│    Direct P2P (если возможно)│◄──────┘       │
│                  └─────────────────────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### ICE Candidates

```python
# WebRTC ICE кандидаты от Telegram
{
    "candidates": [
        {
            "ip": "91.108.56.xxx",
            "port": 553,
            "protocol": "udp",
            "type": "relay",     # Telegram reflector
            "foundation": "...",
            "priority": ...
        }
    ],
    "fingerprints": [...],
    "ufrag": "...",
    "pwd": "..."
}
```

---

## Практические примеры

### Пример 1: Простой видеочат

```python
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, GroupCallConfig

app = Client("session", api_id=..., api_hash="...")
pytg = PyTgCalls(app)

@app.on_message(filters.command("play"))
async def play_video(client, message):
    await pytg.play(
        message.chat.id,
        'video.mp4',  # Автоопределение → видеочат
        config=GroupCallConfig(auto_start=True)
    )

pytg.start()
app.run()
```

### Пример 2: Видеочат с аудиофайлом (placeholder)

```python
from pytgcalls.types import MediaStream, AudioQuality, VideoQuality

async def play_audio_as_videochat(chat_id, audio_file, placeholder_image):
    """
    Воспроизводит аудиофайл в видеочате с placeholder-изображением.
    """
    media = MediaStream(
        placeholder_image,              # PNG/JPG изображение
        audio_path=audio_file,          # MP3/FLAC/OGG файл
        audio_parameters=AudioQuality.HIGH,
        video_parameters=VideoQuality.HD_720p,
    )
    
    await pytg.play(
        chat_id,
        media,
        config=GroupCallConfig(auto_start=True)
    )
```

### Пример 3: Обработка событий

```python
from pytgcalls import filters as fl
from pytgcalls.types import StreamEnded, ChatUpdate

@pytg.on_update(fl.stream_end())
async def on_stream_ended(client, update: StreamEnded):
    print(f"Stream ended in {update.chat_id}")
    # Можно запустить следующий трек

@pytg.on_update(fl.chat_update(ChatUpdate.Status.KICKED))
async def on_kicked(client, update: ChatUpdate):
    print(f"Kicked from {update.chat_id}")
```

### Пример 4: YouTube стриминг

```python
async def play_youtube(chat_id, youtube_url):
    """
    PyTgCalls автоматически использует yt-dlp для YouTube.
    """
    await pytg.play(
        chat_id,
        youtube_url,  # https://youtube.com/watch?v=...
        config=GroupCallConfig(auto_start=True)
    )
```

---

## Ссылки на документацию

### Официальная документация Telegram

| Ресурс | URL |
|--------|-----|
| Telegram APIs | https://core.telegram.org/ |
| E2E Video Calls | https://core.telegram.org/api/end-to-end/video-calls |
| MTProto Protocol | https://core.telegram.org/mtproto |
| API Methods | https://core.telegram.org/methods |
| TDLib | https://core.telegram.org/tdlib |

### Репозитории

| Проект | URL | Описание |
|--------|-----|----------|
| tgcalls | https://github.com/TelegramMessenger/tgcalls | Официальная C++ библиотека |
| PyTgCalls | https://github.com/pytgcalls/pytgcalls | Python обёртка |
| NTgCalls | https://github.com/pytgcalls/ntgcalls | Cython биндинг |

### MTProto методы для звонков

| Метод | Документация |
|-------|--------------|
| phone.createGroupCall | https://core.telegram.org/method/phone.createGroupCall |
| phone.joinGroupCall | https://core.telegram.org/method/phone.joinGroupCall |
| phone.leaveGroupCall | https://core.telegram.org/method/phone.leaveGroupCall |
| phone.discardGroupCall | https://core.telegram.org/method/phone.discardGroupCall |

---

## Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 21.12.2025 | Первоначальная версия документации |

---

> **Примечание:** Эта документация создана на основе официальных источников Telegram и исходного кода PyTgCalls. При обновлении библиотек рекомендуется сверяться с актуальной документацией.
