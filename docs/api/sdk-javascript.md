# JavaScript/TypeScript SDK Integration Guide

> **Spec**: 026-api-webhook-ecosystem
> **Версия**: 1.0
> **Дата**: 2026-01-23

## Обзор / Overview

Official JavaScript/TypeScript SDK for the Sattva Streaming Platform API.
Официальный JavaScript/TypeScript SDK для API Sattva Streaming Platform.

The SDK provides a complete JavaScript interface to all Sattva API endpoints with full TypeScript support, works in Node.js, browsers, and edge runtimes.
SDK предоставляет полный JavaScript интерфейс ко всем endpoint'ам Sattva API с полной поддержкой TypeScript, работает в Node.js, браузерах и edge runtime.

## Установка / Installation

### Using npm (Рекомендуется / Recommended)

```bash
npm install @sattva/api-client
```

### Using yarn

```bash
yarn add @sattva/api-client
```

### Using pnpm

```bash
pnpm add @sattva/api-client
```

### Features / Возможности

- 🚀 Full TypeScript support with comprehensive types / Полная поддержка TypeScript с исчерпывающими типами
- 🔑 API key authentication / Аутентификация через API ключи
- 📡 Webhook signature verification / Проверка подписи вебхуков
- 🔄 Automatic retry logic for rate-limited requests / Автоматический повтор при rate limit
- 🎯 All API resources supported / Все ресурсы API поддерживаются
- 📦 Works in Node.js, browsers, and edge runtimes / Работает в Node.js, браузерах и edge runtime
- 🌐 ESM and CommonJS support / Поддержка ESM и CommonJS

## Quick Start / Быстрый старт

### Basic Initialization (Базовая инициализация)

```typescript
import { SattvaClient } from '@sattva/api-client';

// Initialize client with API key
// Инициализация клиента с API ключом
const client = new SattvaClient({
  apiKey: 'your-api-key-here',
  baseUrl: 'https://api.sattva.io/api/v1'
});

// List all streams
// Получить список всех стримов
const streams = await client.streams.list();
console.log(streams);
```

### Using Environment Variables (Использование переменных окружения)

```typescript
// .env file
SATTVA_API_KEY=sk_live_xxxxxxxxxxxx
SATTVA_API_URL=https://api.sattva.io/api/v1

// TypeScript/JavaScript code
// TypeScript/JavaScript код
import { SattvaClient } from '@sattva/api-client';

const client = new SattvaClient({
  apiKey: process.env.SATTVA_API_KEY!,
  baseUrl: process.env.SATTVA_API_URL || 'https://api.sattva.io/api/v1'
});
```

## Authentication / Аутентификация

### API Key Setup (Настройка API ключа)

```typescript
import { SattvaClient } from '@sattva/api-client';

// Create API key in dashboard or via API
// Создайте API ключ в дашборде или через API
const client = new SattvaClient({
  apiKey: 'sk_live_xxxxxxxxxxxx'  // Your API key / Ваш API ключ
});
```

### API Key Security (Безопасность API ключей)

⚠️ **Security Best Practices / Рекомендации по безопасности:**

- Never commit API keys to version control / Никогда не коммитьте API ключи в репозиторий
- Use environment variables in production / Используйте переменные окружения в production
- Rotate API keys regularly / Регулярно обновляйте API ключи
- Use separate keys for dev/prod / Используйте разные ключи для разработки и продакшна

```typescript
import dotenv from 'dotenv';
dotenv.config();

import { SattvaClient } from '@sattva/api-client';

const client = new SattvaClient({
  apiKey: process.env.SATTVA_API_KEY!
});
```

## Resources / Ресурсы

### Streams (Стримы)

```typescript
import { SattvaClient } from '@sattva/api-client';

const client = new SattvaClient({ apiKey: 'your-api-key' });

// List all streams / Список всех стримов
const streams = await client.streams.list();

// Get specific stream / Получить конкретный стрим
const stream = await client.streams.get('stream-123');

// Start a stream / Запустить стрим
const response = await client.streams.start('channel-123');
console.log('Stream started:', response.streamId);

// Stop a stream / Остановить стрим
await client.streams.stop('stream-123');

// Restart a stream / Перезапустить стрим
const restarted = await client.streams.restart('channel-123');
```

### Channels (Каналы)

```typescript
// List channels / Список каналов
const channels = await client.channels.list();

// Get specific channel / Получить конкретный канал
const channel = await client.channels.get('channel-123');

// Create channel / Создать канал
const newChannel = await client.channels.create({
  name: 'My Channel',
  description: 'Channel description',
  url: 'https://example.com/stream'
});

// Update channel / Обновить канал
await client.channels.update('channel-123', {
  name: 'Updated Channel Name'
});

// Delete channel / Удалить канал
await client.channels.delete('channel-123');
```

### Playlists (Плейлисты)

```typescript
// List playlists / Список плейлистов
const playlists = await client.playlists.list();

// Get playlist / Получить плейлист
const playlist = await client.playlists.get('playlist-123');

// Create playlist / Создать плейлист
const playlist = await client.playlists.create({
  name: 'My Playlist',
  trackIds: ['track-1', 'track-2']
});

// Update playlist / Обновить плейлист
await client.playlists.update('playlist-123', {
  name: 'Updated Playlist'
});

// Reorder tracks / Переупорядочить треки
await client.playlists.reorder('playlist-123', {
  trackIds: ['track-2', 'track-1']
});

// Delete playlist / Удалить плейлист
await client.playlists.delete('playlist-123');
```

### Webhooks (Вебхуки)

```typescript
// List webhooks / Список вебхуков
const webhooks = await client.webhooks.list();

// Get webhook / Получить вебхук
const webhook = await client.webhooks.get('webhook-123');

// Create webhook / Создать вебхук
const webhook = await client.webhooks.create({
  url: 'https://your-app.com/webhooks',
  eventTypes: ['stream.started', 'stream.stopped']
});
// IMPORTANT: Save the secret immediately!
// ВАЖНО: Сразу сохраните секрет!
const webhookSecret = webhook.secret;

// Test webhook / Протестировать вебхук
await client.webhooks.test('webhook-123');

// Rotate webhook secret / Обновить секрет вебхука
const newSecret = await client.webhooks.rotateSecret('webhook-123');

// List webhook events / Список событий вебхука
const events = await client.webhooks.listEvents('webhook-123');

// Delete webhook / Удалить вебхук
await client.webhooks.delete('webhook-123');
```

### API Keys (API ключи)

```typescript
// List API keys / Список API ключей
const keys = await client.apiKeys.list();

// Create API key / Создать API ключ
const key = await client.apiKeys.create({
  name: 'Read-only Integration',
  scopes: ['read:streams', 'read:playlists']
});
// IMPORTANT: Save the key value immediately!
// ВАЖНО: Сразу сохраните значение ключа!
const apiKeyValue = key.key;

// Revoke API key / Отозвать API ключ
await client.apiKeys.revoke('key-123');
```

## Error Handling (Обработка ошибок)

### Exception Types (Типы исключений)

```typescript
import {
  SattvaAPIError,
  AuthenticationError,
  RateLimitError,
  NotFoundError,
  ValidationError
} from '@sattva/api-client';

try {
  await client.streams.start('channel-123');
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key / Неверный API ключ');
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limit exceeded. Retry after: ${error.retryAfter} seconds`);
    console.error(`Превышен лимит запросов. Повторите через: ${error.retryAfter} секунд`);
  } else if (error instanceof NotFoundError) {
    console.error('Channel not found / Канал не найден');
  } else if (error instanceof ValidationError) {
    console.error('Validation error:', error.errors);
    console.error('Ошибка валидации:', error.errors);
  } else {
    console.error('API error:', error.message);
  }
}
```

### Async/Await Pattern (Паттерн Async/Await)

```typescript
async function manageStream() {
  try {
    const stream = await client.streams.get('stream-123');
    console.log('Stream:', stream);
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}
```

## Webhook Signature Verification (Проверка подписи вебхука)

### Verify Webhooks (Проверка вебхуков)

```typescript
import { verifyWebhookSignature } from '@sattva/api-client/webhook';

// Express.js example / Пример для Express.js
import express from 'express';

const app = express();

app.post('/webhooks', (req, res) => {
  const signature = req.headers['x-sattva-signature'] as string;
  const payload = req.body;
  const secret = 'your-webhook-secret';

  if (verifyWebhookSignature(payload, signature, secret)) {
    // Signature is valid, process webhook
    // Подпись валидна, обрабатываем вебхук
    console.log('Event type:', payload.event_type);
    console.log('Event data:', payload.data);

    // Process event based on type / Обработать событие по типу
    switch (payload.event_type) {
      case 'stream.started':
        handleStreamStarted(payload.data);
        break;
      case 'stream.stopped':
        handleStreamStopped(payload.data);
        break;
      case 'stream.error':
        handleStreamError(payload.data);
        break;
    }

    res.sendStatus(200);
  } else {
    // Invalid signature / Неверная подпись
    console.warn('Invalid webhook signature');
    res.sendStatus(401);
  }
});
```

### NestJS Example (Пример для NestJS)

```typescript
import { Controller, Post, Body, Headers, HttpCode, HttpStatus } from '@nestjs/common';
import { verifyWebhookSignature } from '@sattva/api-client/webhook';

@Controller('webhooks')
export class WebhooksController {
  @Post()
  @HttpCode(HttpStatus.OK)
  handleWebhook(
    @Body() payload: any,
    @Headers('x-sattva-signature') signature: string
  ) {
    const secret = 'your-webhook-secret';

    if (verifyWebhookSignature(payload, signature, secret)) {
      // Process webhook / Обработать вебхук
      this.processEvent(payload);
      return { status: 'ok' };
    } else {
      throw new UnauthorizedException('Invalid signature');
    }
  }

  private processEvent(event: any) {
    // Event processing logic / Логика обработки события
  }
}
```

### Next.js Example (Пример для Next.js)

```typescript
// pages/api/webhooks.ts
import type { NextApiRequest, NextApiResponse } from 'next';
import { verifyWebhookSignature } from '@sattva/api-client/webhook';

export default function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const signature = req.headers['x-sattva-signature'] as string;
  const secret = process.env.WEBHOOK_SECRET!;

  if (verifyWebhookSignature(req.body, signature, secret)) {
    // Process webhook / Обработать вебхук
    console.log('Received event:', req.body.event_type);
    res.status(200).json({ status: 'ok' });
  } else {
    res.status(401).json({ error: 'Invalid signature' });
  }
}
```

## Advanced Usage (Расширенное использование)

### Custom Configuration (Кастомная конфигурация)

```typescript
const client = new SattvaClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.sattva.io/api/v1',
  timeout: 30000,      // Request timeout in milliseconds / Таймаут запроса в мс
  maxRetries: 3,       // Max retries for rate-limited requests / Максимум попыток при rate limit
  retryDelay: 1000     // Initial retry delay in milliseconds / Начальная задержка в мс
});
```

### TypeScript Types (Типы TypeScript)

```typescript
import { SattvaClient, Stream, Playlist, Webhook } from '@sattva/api-client';

const client: SattvaClient = new SattvaClient({
  apiKey: 'your-api-key'
});

// Types are automatically inferred
// Типы выводятся автоматически
const streams: Stream[] = await client.streams.list();
const playlist: Playlist = await client.playlists.get('playlist-123');
const webhook: Webhook = await client.webhooks.create({
  url: 'https://example.com/webhook',
  eventTypes: ['stream.started']
});
```

### Browser Usage (Использование в браузере)

```typescript
// Works in modern browsers
// Работает в современных браузерах
import { SattvaClient } from '@sattva/api-client';

// Browser-specific configuration
// Конфигурация для браузера
const client = new SattvaClient({
  apiKey: browserApiKey,
  baseUrl: 'https://api.sattva.io/api/v1'
});

// Make requests from browser
// Делать запросы из браузера
const streams = await client.streams.list();
console.log('Streams:', streams);
```

### Node.js Usage (Использование в Node.js)

```typescript
// ESM import / Импорт ESM
import { SattvaClient } from '@sattva/api-client';

const client = new SattvaClient({ apiKey: 'your-api-key' });

// CommonJS require / CommonJS require
const { SattvaClient } = require('@sattva/api-client');

const client = new SattvaClient({ apiKey: 'your-api-key' });
```

## Configuration (Конфигурация)

### Client Options (Опции клиента)

| Option / Опция | Type / Тип | Default / По умолчанию | Description / Описание |
|----------------|-----------|----------------------|----------------------|
| `apiKey` | string | — | Your API key / Ваш API ключ |
| `baseUrl` | string | `'https://api.sattva.io/api/v1'` | API base URL / Базовый URL API |
| `timeout` | number | `30000` | Request timeout in ms / Таймаут запроса в мс |
| `maxRetries` | number | `3` | Max retries on rate limit / Максимум повторов при rate limit |
| `retryDelay` | number | `1000` | Initial retry delay in ms / Начальная задержка в мс |

### Rate Limiting (Rate limiting)

```typescript
// SDK automatically handles rate limiting with exponential backoff
// SDK автоматически обрабатывает rate limiting с экспоненциальной задержкой
const client = new SattvaClient({
  apiKey: 'your-api-key',
  maxRetries: 3,      // Max retries / Максимум попыток
  retryDelay: 1000    // Initial delay: 1000ms, 2000ms, 4000ms...
                      // Начальная задержка: 1000мс, 2000мс, 4000мс...
});

// When rate limit is hit (429), SDK automatically retries
// При превышении лимита (429) SDK автоматически повторяет запрос
```

## Testing (Тестирование)

### Jest Tests (Jest тесты)

```typescript
import { SattvaClient } from '@sattva/api-client';

describe('SattvaClient', () => {
  let client: SattvaClient;

  beforeEach(() => {
    client = new SattvaClient({
      apiKey: 'test-api-key'
    });
  });

  test('should list streams', async () => {
    const streams = await client.streams.list();
    expect(Array.isArray(streams)).toBe(true);
  });

  test('should handle errors', async () => {
    await expect(
      client.streams.get('invalid-id')
    ).rejects.toThrow(NotFoundError);
  });
});
```

### Mocking API Calls (Мокинг API вызовов)

```typescript
import { SattvaClient } from '@sattva/api-client';

// Mock fetch for testing
// Мокаем fetch для тестов
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ streams: [] })
  } as Response)
);

const client = new SattvaClient({ apiKey: 'test-key' });
const streams = await client.streams.list();
expect(streams).toEqual([]);
```

## Development (Разработка)

### Building (Сборка)

```bash
npm run build
```

### Running Tests (Запуск тестов)

```bash
npm test
```

### Code Quality (Качество кода)

```bash
# Format code / Форматировать код
npm run format    # Prettier

# Lint code / Проверить код
npm run lint      # ESLint

# Type check / Проверка типов
npm run type-check # TypeScript
```

## Event Types (Типы событий)

Webhook events available for subscription / Вебхук-события, доступные для подписки:

| Event Type | Description / Описание |
|------------|----------------------|
| `stream.started` | Stream has started / Стрим запущен |
| `stream.stopped` | Stream has stopped / Стрим остановлен |
| `stream.paused` | Stream has paused / Стрим на паузе |
| `stream.resumed` | Stream has resumed / Стрим возобновлен |
| `stream.error` | Stream error occurred / Ошибка стрима |
| `viewer.milestone` | Viewer milestone reached / Достигнут milestone зрителей |
| `viewer.joined` | Viewer joined the stream / Зритель присоединился |
| `viewer.left` | Viewer left the stream / Зритель покинул стрим |
| `track.started` | Track started playing / Трек начал воспроизводиться |
| `track.completed` | Track completed / Трек закончил воспроизводиться |
| `track.failed` | Track failed to play / Трек не воспроизвелся |
| `track.skipped` | Track was skipped / Трек пропущен |

## Common Use Cases (Частые случаи использования)

### React Integration (Интеграция с React)

```typescript
import { useState, useEffect } from 'react';
import { SattvaClient } from '@sattva/api-client';

const client = new SattvaClient({
  apiKey: process.env.REACT_APP_API_KEY!
});

function StreamsList() {
  const [streams, setStreams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStreams() {
      try {
        const data = await client.streams.list();
        setStreams(data);
      } catch (error) {
        console.error('Error loading streams:', error);
      } finally {
        setLoading(false);
      }
    }

    loadStreams();
  }, []);

  if (loading) return <div>Loading...</div>;
  return (
    <ul>
      {streams.map(stream => (
        <li key={stream.id}>{stream.name}</li>
      ))}
    </ul>
  );
}
```

### Vue.js Integration (Интеграция с Vue.js)

```typescript
import { ref, onMounted } from 'vue';
import { SattvaClient } from '@sattva/api-client';

const client = new SattvaClient({
  apiKey: import.meta.env.VITE_API_KEY
});

export function useStreams() {
  const streams = ref([]);
  const loading = ref(true);

  onMounted(async () => {
    try {
      streams.value = await client.streams.list();
    } catch (error) {
      console.error('Error:', error);
    } finally {
      loading.value = false;
    }
  });

  return { streams, loading };
}
```

### Server Actions (Next.js App Router)

```typescript
// app/actions.ts
'use server';

import { SattvaClient } from '@sattva/api-client';

const client = new SattvaClient({
  apiKey: process.env.SATTVA_API_KEY!
});

export async function getStreams() {
  try {
    return await client.streams.list();
  } catch (error) {
    console.error('Error fetching streams:', error);
    return [];
  }
}

export async function startStream(channelId: string) {
  try {
    return await client.streams.start(channelId);
  } catch (error) {
    console.error('Error starting stream:', error);
    throw error;
  }
}
```

## Troubleshooting (Решение проблем)

### Common Issues (Частые проблемы)

| Problem / Проблема | Solution / Решение |
|-------------------|-------------------|
| `AuthenticationError` | Check API key is valid / Проверьте валидность API ключа |
| `RateLimitError` | SDK auto-retries, but consider reducing request frequency / SDK автоматически повторяет, но рассмотрите уменьшение частоты запросов |
| `NotFoundError` | Verify resource ID exists / Проверьте существование ID ресурса |
| TypeError in browser | Ensure browser supports Web Crypto API / Убедитесь, что браузер поддерживает Web Crypto API |

### Debug Logging (Debug-логирование)

```typescript
// Enable debug logging / Включить debug-логирование
const client = new SattvaClient({
  apiKey: 'your-api-key',
  debug: true  // Logs all HTTP requests / Логирует все HTTP запросы
});
```

## Browser Support (Поддержка браузеров)

SDK works in modern browsers with these features:
SDK работает в современных браузерах с следующими возможностями:

- ES2017+ (async/await)
- Fetch API
- Web Crypto API (or polyfilled)

### Browser Polyfills (Полифилы для браузеров)

```typescript
// Add polyfills for older browsers
// Добавить полифилы для старых браузеров
import 'crypto-polyfill';
import 'whatwg-fetch';
```

## Related Documents (Связанные документы)

- [API Reference](./reference.md)
- [Authentication Guide](./authentication.md)
- [Webhooks Guide](./webhooks.md)
- [API Versioning](./versioning.md)
- [026 Spec](../../specs/026-api-webhook-ecosystem/)

## Support & Resources (Поддержка и ресурсы)

- **Documentation / Документация**: [https://docs.sattva.io](https://docs.sattva.io)
- **GitHub / GitHub**: [https://github.com/sattva/sattva-js-sdk](https://github.com/sattva/sattva-js-sdk)
- **npm Package / npm пакет**: [@sattva/api-client](https://www.npmjs.com/package/@sattva/api-client)
- **Bug Reports / Баг-репорты**: [GitHub Issues](https://github.com/sattva/sattva-js-sdk/issues)
- **Email / Email**: api@sattva.io

## License (Лицензия)

MIT
