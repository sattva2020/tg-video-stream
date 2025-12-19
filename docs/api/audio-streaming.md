# Audio Streaming API

**Версия**: 1.0.0  
**Feature**: 017-audio-streaming-enhancements  
**Дата**: 2024-12-02

## Обзор

API для управления расширенными функциями аудио-стриминга:
- Управление скоростью и тональностью воспроизведения
- Перемотка и позиционирование
- Радио-потоки
- Эквалайзер с пресетами
- Приоритетные очереди
- Планирование воспроизведения
- Тексты песен (Genius API)
- Распознавание музыки (Shazam)
- Мульти-канальное управление
- Локализация интерфейса

## Аутентификация

Все endpoints требуют JWT токен:
```
Authorization: Bearer <access_token>
```

## Rate Limiting

| Endpoint группа | Лимит | Окно |
|-----------------|-------|------|
| Playback | 60 req | 1 min |
| Radio | 30 req | 1 min |
| Recognition | 10 req | 1 min |
| Lyrics | 20 req | 1 min |

При превышении лимита возвращается `429 Too Many Requests`.

---

## Playback API

### Скорость воспроизведения

### `PUT /api/playback/speed`

Изменить скорость воспроизведения.

**Request Body:**
```json
{
  "speed": 1.5,
  "channel_id": 123456789
}
```

**Параметры:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| speed | float | Да | Скорость (0.5 - 2.0) |
| channel_id | int | Нет | ID канала (по умолчанию активный) |

**Response (200 OK):**
```json
{
  "success": true,
  "speed": 1.5,
  "channel_id": 123456789
}
```

**Ошибки:**
- `400` - Некорректное значение скорости
- `401` - Не авторизован
- `429` - Rate limit exceeded

---

### Тональность

### `PUT /api/playback/pitch`

Изменить тональность (высоту тона).

**Request Body:**
```json
{
  "semitones": 2,
  "pitch_correction": true,
  "channel_id": 123456789
}
```

**Параметры:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| semitones | int | Да | Полутоны (-12 до +12) |
| pitch_correction | bool | Нет | Коррекция тона (default: true) |
| channel_id | int | Нет | ID канала |

**Response (200 OK):**
```json
{
  "success": true,
  "semitones": 2,
  "pitch_correction": true
}
```

---

### Перемотка

### `POST /api/playback/seek`

Перемотать к указанной позиции.

**Request Body:**
```json
{
  "position": 90,
  "channel_id": 123456789
}
```

**Параметры:**
| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| position | int | Да | Позиция в секундах |
| channel_id | int | Нет | ID канала |

**Response (200 OK):**
```json
{
  "success": true,
  "position": 90,
  "duration": 240
}
```

---

### `GET /api/playback/position`

Получить текущую позицию воспроизведения.

**Query Parameters:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| channel_id | int | ID канала (опционально) |

**Response (200 OK):**
```json
{
  "position": 45,
  "duration": 240,
  "progress": 0.1875,
  "is_playing": true,
  "track": {
    "title": "Song Name",
    "artist": "Artist Name"
  }
}
```

---

## Equalizer API

### `GET /api/playback/equalizer/presets`

Получить список доступных пресетов эквалайзера.

**Response (200 OK):**
```json
{
  "presets": [
    {
      "id": "flat",
      "name": "Flat",
      "description": "Нейтральный звук без коррекции",
      "bands": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    },
    {
      "id": "bass_boost",
      "name": "Bass Boost",
      "description": "Усиление низких частот",
      "bands": [6, 5, 4, 2, 0, 0, 0, 0, 0, 0]
    },
    {
      "id": "meditation",
      "name": "Meditation",
      "description": "Мягкий релаксирующий звук",
      "bands": [2, 1, 0, -1, -2, -1, 0, 1, 2, 3]
    }
  ]
}
```

---

### `PUT /api/playback/equalizer`

Применить пресет эквалайзера.

**Request Body:**
```json
{
  "preset": "bass_boost",
  "channel_id": 123456789
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "preset": "bass_boost",
  "bands": [6, 5, 4, 2, 0, 0, 0, 0, 0, 0]
}
```

---

## Radio API

### `POST /api/radio/streams`

Добавить новую радиостанцию.

**Request Body:**
```json
{
  "name": "My Radio",
  "url": "https://stream.example.com/radio.mp3",
  "genre": "electronic",
  "description": "24/7 Electronic Music"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "name": "My Radio",
  "url": "https://stream.example.com/radio.mp3",
  "genre": "electronic",
  "is_active": true,
  "created_at": "2024-12-02T10:00:00Z"
}
```

---

### `GET /api/radio/streams`

Получить список радиостанций.

**Query Parameters:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| genre | string | Фильтр по жанру |
| active | bool | Только активные |
| limit | int | Количество (default: 20) |
| offset | int | Смещение |

**Response (200 OK):**
```json
{
  "streams": [
    {
      "id": 1,
      "name": "My Radio",
      "url": "https://stream.example.com/radio.mp3",
      "genre": "electronic",
      "is_active": true,
      "listeners_count": 42
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

## Lyrics API

### `GET /api/lyrics/{track_id}`

Получить текст песни.

**Path Parameters:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| track_id | string | ID трека или "current" |

**Response (200 OK):**
```json
{
  "track_id": "abc123",
  "title": "Song Name",
  "artist": "Artist Name",
  "lyrics": "Verse 1...\n\nChorus...",
  "source": "genius",
  "synced": false,
  "cached": true,
  "cached_at": "2024-12-02T10:00:00Z"
}
```

**Response (404 Not Found):**
```json
{
  "error": "Lyrics not found",
  "searched": {
    "title": "Song Name",
    "artist": "Artist Name"
  }
}
```

---

## Recognition API

### `POST /api/recognition/identify`

Распознать музыку из аудиофайла.

**Request:**
```
Content-Type: multipart/form-data

audio: <binary file>
```

**Response (200 OK):**
```json
{
  "recognized": true,
  "track": {
    "title": "Song Name",
    "artist": "Artist Name",
    "album": "Album Name",
    "release_date": "2024-01-15",
    "genres": ["pop", "electronic"],
    "cover_url": "https://example.com/cover.jpg"
  },
  "confidence": 0.95
}
```

**Response (404 Not Found):**
```json
{
  "recognized": false,
  "message": "Could not recognize the audio"
}
```

---

## Scheduler API

### `POST /api/scheduler/schedules`

Создать расписание воспроизведения.

**Request Body:**
```json
{
  "playlist_id": 1,
  "time": "08:00",
  "days": ["mon", "tue", "wed", "thu", "fri"],
  "channel_id": 123456789,
  "enabled": true
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "playlist_id": 1,
  "time": "08:00",
  "days": ["mon", "tue", "wed", "thu", "fri"],
  "next_run": "2024-12-03T08:00:00Z",
  "enabled": true
}
```

---

### `GET /api/scheduler/schedules`

Получить список расписаний.

**Response (200 OK):**
```json
{
  "schedules": [
    {
      "id": 1,
      "playlist": {
        "id": 1,
        "name": "Morning Playlist"
      },
      "time": "08:00",
      "days": ["mon", "tue", "wed", "thu", "fri"],
      "next_run": "2024-12-03T08:00:00Z",
      "last_run": "2024-12-02T08:00:00Z",
      "enabled": true
    }
  ],
  "total": 1
}
```

---

## I18n API

### `GET /api/i18n/languages`

Получить список поддерживаемых языков.

**Response (200 OK):**
```json
{
  "languages": [
    {
      "code": "ru",
      "name": "Russian",
      "nativeName": "Русский",
      "flag": "🇷🇺",
      "isDefault": true
    },
    {
      "code": "en",
      "name": "English",
      "nativeName": "English",
      "flag": "🇬🇧",
      "isDefault": false
    },
    {
      "code": "uk",
      "name": "Ukrainian",
      "nativeName": "Українська",
      "flag": "🇺🇦",
      "isDefault": false
    },
    {
      "code": "es",
      "name": "Spanish",
      "nativeName": "Español",
      "flag": "🇪🇸",
      "isDefault": false
    }
  ],
  "defaultLanguage": "ru",
  "totalCount": 4
}
```

---

## Коды ошибок

| Код | Описание |
|-----|----------|
| 400 | Bad Request - некорректные параметры |
| 401 | Unauthorized - требуется авторизация |
| 403 | Forbidden - недостаточно прав |
| 404 | Not Found - ресурс не найден |
| 429 | Too Many Requests - превышен лимит |
| 500 | Internal Server Error - ошибка сервера |

## Примеры использования

### JavaScript/TypeScript

```typescript
// Изменить скорость
const response = await fetch('/api/playback/speed', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ speed: 1.5 }),
});

// Получить позицию
const position = await fetch('/api/playback/position', {
  headers: { 'Authorization': `Bearer ${token}` },
}).then(r => r.json());

console.log(`Position: ${position.position}s / ${position.duration}s`);
```

### cURL

```bash
# Получить пресеты эквалайзера
curl -X GET "https://api.example.com/api/playback/equalizer/presets" \
  -H "Authorization: Bearer $TOKEN"

# Применить пресет
curl -X PUT "https://api.example.com/api/playback/equalizer" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"preset": "bass_boost"}'
```
