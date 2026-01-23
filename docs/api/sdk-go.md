# Go SDK Integration Guide

> **Spec**: 026-api-webhook-ecosystem
> **Версия**: 1.0
> **Дата**: 2026-01-23

## Обзор / Overview

Official Go SDK for the Sattva Streaming Platform API.
Официальный Go SDK для API Sattva Streaming Platform.

The SDK provides an idiomatic Go interface to all Sattva API endpoints, with full context support, proper error handling, and type safety.
SDK предоставляет идиоматичный Go интерфейс ко всем endpoint'ам Sattva API с полной поддержкой context, правильной обработкой ошибок и типобезопасностью.

## Установка / Installation

### Using go get (Рекомендуется / Recommended)

```bash
go get github.com/sattva/sattva-go-sdk
```

### Module Setup (Настройка модуля)

```bash
# Initialize new module / Инициализировать новый модуль
go mod init myapp

# Add SDK dependency / Добавить зависимость SDK
go get github.com/sattva/sattva-go-sdk

# Download dependencies / Скачать зависимости
go mod download
```

## Quick Start / Быстрый старт

### Basic Initialization (Базовая инициализация)

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/sattva/sattva-go-sdk"
)

func main() {
    // Initialize client with API key
    // Инициализация клиента с API ключом
    client := sattva.NewClient(
        "your-api-key-here",
        sattva.WithBaseURL("https://api.sattva.io/api/v1"),
    )

    ctx := context.Background()

    // List all streams
    // Получить список всех стримов
    streams, err := client.Streams.List(ctx)
    if err != nil {
        log.Fatal(err)
    }

    for _, stream := range streams {
        fmt.Printf("Stream: %s - %s\n", stream.Name, stream.Status)
    }
}
```

### Using Environment Variables (Использование переменных окружения)

```go
package main

import (
    "context"
    "log"
    "os"

    "github.com/sattva/sattva-go-sdk"
)

func main() {
    // Recommended for production
    // Рекомендуется для production
    apiKey := os.Getenv("SATTVA_API_KEY")
    baseURL := os.Getenv("SATTVA_API_URL")

    client := sattva.NewClient(
        apiKey,
        sattva.WithBaseURL(baseURL),
    )

    ctx := context.Background()
    streams, err := client.Streams.List(ctx)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Found %d streams\n", len(streams))
}
```

## Authentication / Аутентификация

### API Key Setup (Настройка API ключа)

```go
package main

import "github.com/sattva/sattva-go-sdk"

func main() {
    // Create API key in dashboard or via API
    // Создайте API ключ в дашборде или через API
    client := sattva.NewClient(
        "sk_live_xxxxxxxxxxxx",  // Your API key / Ваш API ключ
    )
}
```

### API Key Security (Безопасность API ключей)

⚠️ **Security Best Practices / Рекомендации по безопасности:**

- Never commit API keys to version control / Никогда не коммитьте API ключи в репозиторий
- Use environment variables in production / Используйте переменные окружения в production
- Rotate API keys regularly / Регулярно обновляйте API ключи
- Use separate keys for dev/prod / Используйте разные ключи для разработки и продакшна

```go
package main

import (
    "log"
    "os"

    "github.com/sattva/sattva-go-sdk"
)

func main() {
    // Load from environment / Загрузить из окружения
    apiKey := os.Getenv("SATTVA_API_KEY")
    if apiKey == "" {
        log.Fatal("SATTVA_API_KEY environment variable is required")
    }

    client := sattva.NewClient(apiKey)
}
```

## Resources / Ресурсы

### Streams (Стримы)

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/sattva/sattva-go-sdk"
)

func main() {
    client := sattva.NewClient("your-api-key")
    ctx := context.Background()

    // List all streams / Список всех стримов
    streams, err := client.Streams.List(ctx)
    if err != nil {
        log.Fatal(err)
    }

    // Get specific stream / Получить конкретный стрим
    stream, err := client.Streams.Get(ctx, "stream-123")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Stream: %v\n", stream.Name)

    // Start a stream / Запустить стрим
    response, err := client.Streams.Start(ctx, "channel-123")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Stream started: %s\n", response.StreamID)

    // Stop a stream / Остановить стрим
    _, err = client.Streams.Stop(ctx, "stream-123")
    if err != nil {
        log.Fatal(err)
    }

    // Pause a stream / Поставить стрим на паузу
    _, err = client.Streams.Pause(ctx, "stream-123")
    if err != nil {
        log.Fatal(err)
    }

    // Resume a stream / Продолжить стрим
    _, err = client.Streams.Resume(ctx, "stream-123")
    if err != nil {
        log.Fatal(err)
    }
}
```

### Playlists (Плейлисты)

```go
// List playlists / Список плейлистов
playlists, err := client.Playlists.List(ctx)
if err != nil {
    log.Fatal(err)
}

// Get playlist / Получить плейлист
playlist, err := client.Playlists.Get(ctx, "playlist-123")
if err != nil {
    log.Fatal(err)
}

// Create playlist / Создать плейлист
playlist, err := client.Playlists.Create(ctx, &sattva.PlaylistCreateRequest{
    Name:        "My Playlist",
    Description: "Favorite tracks",
})
if err != nil {
    log.Fatal(err)
}

// Update playlist / Обновить плейлист
updated, err := client.Playlists.Update(ctx, playlist.ID, &sattva.PlaylistUpdateRequest{
    Name:     "Updated Name",
    TrackIDs: []string{"track-1", "track-2", "track-3"},
})
if err != nil {
    log.Fatal(err)
}

// Reorder tracks / Переупорядочить треки
err = client.Playlists.Reorder(ctx, playlist.ID, &sattva.PlaylistReorderRequest{
    TrackIDs: []string{"track-3", "track-1", "track-2"},
})
if err != nil {
    log.Fatal(err)
}

// Get playlist status / Получить статус плейлиста
status, err := client.Playlists.GetStatus(ctx, playlist.ID)
if err != nil {
    log.Fatal(err)
}
fmt.Printf("Current track: %s\n", status.CurrentTrack)

// Delete playlist / Удалить плейлист
err = client.Playlists.Delete(ctx, playlist.ID)
if err != nil {
    log.Fatal(err)
}
```

### Channels (Каналы)

```go
// List channels / Список каналов
channels, err := client.Channels.List(ctx)
if err != nil {
    log.Fatal(err)
}

// Get channel / Получить канал
channel, err := client.Channels.Get(ctx, "channel-123")
if err != nil {
    log.Fatal(err)
}

// Create channel / Создать канал
channel, err = client.Channels.Create(ctx, &sattva.ChannelCreateRequest{
    Name:        "My Channel",
    Description: "Channel description",
    URL:         "https://example.com/stream",
})
if err != nil {
    log.Fatal(err)
}

// Update channel / Обновить канал
updated, err := client.Channels.Update(ctx, channel.ID, &sattva.ChannelUpdateRequest{
    Name: "Updated Channel",
})
if err != nil {
    log.Fatal(err)
}

// Delete channel / Удалить канал
err = client.Channels.Delete(ctx, channel.ID)
if err != nil {
    log.Fatal(err)
}
```

### Webhooks (Вебхуки)

```go
// List webhooks / Список вебхуков
webhooks, err := client.Webhooks.List(ctx)
if err != nil {
    log.Fatal(err)
}

// Get webhook / Получить вебхук
webhook, err := client.Webhooks.Get(ctx, "webhook-123")
if err != nil {
    log.Fatal(err)
}

// Create webhook / Создать вебхук
webhook, err = client.Webhooks.Create(ctx, &sattva.WebhookCreateRequest{
    URL:        "https://your-app.com/webhooks",
    EventTypes: []string{"stream.started", "stream.stopped", "stream.error"},
})
if err != nil {
    log.Fatal(err)
}
// IMPORTANT: Save the secret immediately!
// ВАЖНО: Сразу сохраните секрет!
webhookSecret := webhook.Secret

// Test webhook / Протестировать вебхук
result, err := client.Webhooks.Test(ctx, webhook.ID)
if err != nil {
    log.Fatal(err)
}
fmt.Printf("Test success: %v\n", result.Success)

// Rotate webhook secret / Обновить секрет вебхука
webhook, err = client.Webhooks.RotateSecret(ctx, webhook.ID)
if err != nil {
    log.Fatal(err)
}
newSecret := webhook.Secret // Save new secret / Сохраните новый секрет

// List webhook events / Список событий вебхука
events, err := client.Webhooks.ListEvents(ctx, webhook.ID)
if err != nil {
    log.Fatal(err)
}

for _, event := range events {
    fmt.Printf("Event %s: %s\n", event.EventType, event.Status)
}

// Delete webhook / Удалить вебхук
err = client.Webhooks.Delete(ctx, webhook.ID)
if err != nil {
    log.Fatal(err)
}
```

### API Keys (API ключи)

```go
// List API keys / Список API ключей
keys, err := client.APIKeys.List(ctx)
if err != nil {
    log.Fatal(err)
}

for _, key := range keys {
    fmt.Printf("%s: %v\n", key.Name, key.Scopes)
}

// Create API key / Создать API ключ
key, err := client.APIKeys.Create(ctx, &sattva.APIKeyCreateRequest{
    Name:   "Read-only Integration",
    Scopes: []string{"read:streams", "read:playlists"},
})
if err != nil {
    log.Fatal(err)
}
// IMPORTANT: Save the key value immediately!
// ВАЖНО: Сразу сохраните значение ключа!
apiKeyValue := key.Key

// Revoke API key / Отозвать API ключ
err = client.APIKeys.Revoke(ctx, "key-123")
if err != nil {
    log.Fatal(err)
}
```

## Error Handling (Обработка ошибок)

### Error Types (Типы ошибок)

```go
package main

import (
    "context"
    "errors"
    "log"

    "github.com/sattva/sattva-go-sdk"
)

func main() {
    client := sattva.NewClient("your-api-key")
    ctx := context.Background()

    stream, err := client.Streams.Get(ctx, "stream-123")
    if err != nil {
        var authErr *sattva.AuthenticationError
        var rateLimitErr *sattva.RateLimitError
        var notFoundErr *sattva.NotFoundError

        switch {
        case errors.As(err, &authErr):
            log.Println("Invalid API key / Неверный API ключ")
        case errors.As(err, &rateLimitErr):
            log.Printf("Rate limit exceeded. Retry after: %v",
                rateLimitErr.RetryAfter)
            log.Printf("Превышен лимит запросов. Повторите через: %v",
                rateLimitErr.RetryAfter)
        case errors.As(err, &notFoundErr):
            log.Println("Stream not found / Стрим не найден")
        default:
            log.Printf("API error: %v", err)
            log.Printf("Ошибка API: %v", err)
        }
        return
    }

    log.Printf("Stream: %v\n", stream)
}
```

### Error Wrapping (Обертывание ошибок)

```go
func getStreamName(ctx context.Context, client *sattva.Client, streamID string) (string, error) {
    stream, err := client.Streams.Get(ctx, streamID)
    if err != nil {
        return "", fmt.Errorf("failed to get stream %s: %w", streamID, err)
    }
    return stream.Name, nil
}
```

## Context Support (Поддержка Context)

### Timeouts (Таймауты)

```go
package main

import (
    "context"
    "log"
    "time"

    "github.com/sattva/sattva-go-sdk"
)

func main() {
    client := sattva.NewClient("your-api-key")

    // Create context with timeout
    // Создать context с таймаутом
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    streams, err := client.Streams.List(ctx)
    if err != nil {
        log.Fatal(err)
    }

    log.Printf("Found %d streams\n", len(streams))
}
```

### Cancellation (Отмена)

```go
func main() {
    client := sattva.NewClient("your-api-key")

    // Create cancelable context
    // Создать отменяемый context
    ctx, cancel := context.WithCancel(context.Background())

    // Cancel from another goroutine
    // Отмена из другой goroutine
    go func() {
        time.Sleep(5 * time.Second)
        cancel() // Cancel the request / Отменить запрос
    }()

    streams, err := client.Streams.List(ctx)
    if err != nil {
        if errors.Is(err, context.Canceled) {
            log.Println("Request was canceled / Запрос был отменен")
        }
        return
    }
}
```

## Webhook Signature Verification (Проверка подписи вебхука)

### Verify Webhooks (Проверка вебхуков)

```go
package main

import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "io"
    "log"
    "net/http"

    "github.com/sattva/sattva-go-sdk"
)

func webhookHandler(w http.ResponseWriter, r *http.Request) {
    // Read the payload / Прочитать payload
    payload, err := io.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read body", http.StatusBadRequest)
        return
    }

    // Get signature from header / Получить подпись из заголовка
    signature := r.Header.Get("X-Sattva-Signature")
    secret := "your-webhook-secret"

    // Verify signature / Проверить подпись
    if !sattva.VerifyWebhookSignature(payload, signature, secret) {
        http.Error(w, "Invalid signature", http.StatusUnauthorized)
        return
    }

    // Process the event / Обработать событие
    event := sattva.WebhookEvent{}
    if err := json.Unmarshal(payload, &event); err != nil {
        http.Error(w, "Invalid payload", http.StatusBadRequest)
        return
    }

    log.Printf("Received event: %s\n", event.Type)
    log.Printf("Получено событие: %s\n", event.Type)

    // Process event based on type / Обработать событие по типу
    switch event.Type {
    case "stream.started":
        handleStreamStarted(event)
    case "stream.stopped":
        handleStreamStopped(event)
    case "stream.error":
        handleStreamError(event)
    }

    w.WriteHeader(http.StatusOK)
}

func handleStreamStarted(event sattva.WebhookEvent) {
    // Handle stream started event / Обработать событие запуска стрима
    log.Printf("Stream started: %v\n", event.Data)
}

func handleStreamStopped(event sattva.WebhookEvent) {
    // Handle stream stopped event / Обработать событие остановки стрима
    log.Printf("Stream stopped: %v\n", event.Data)
}

func handleStreamError(event sattva.WebhookEvent) {
    // Handle stream error event / Обработать событие ошибки стрима
    log.Printf("Stream error: %v\n", event.Data)
}
```

### Using with Gorilla Mux (С Gorilla Mux)

```go
package main

import (
    "log"
    "net/http"

    "github.com/gorilla/mux"
    "github.com/sattva/sattva-go-sdk"
)

func main() {
    r := mux.NewRouter()

    r.HandleFunc("/webhooks", webhookHandler).Methods("POST")

    log.Println("Server starting on :8080")
    log.Fatal(http.ListenAndServe(":8080", r))
}
```

## Advanced Usage (Расширенное использование)

### Custom Configuration (Кастомная конфигурация)

```go
package main

import (
    "time"

    "github.com/sattva/sattva-go-sdk"
)

func main() {
    // Configure client with custom options
    // Настроить клиент с кастомными опциями
    client := sattva.NewClient(
        "your-api-key",
        sattva.WithBaseURL("https://api.sattva.io/api/v1"),
        sattva.WithTimeout(30*time.Second),
        sattva.WithMaxRetries(5),
        sattva.WithRetryDelay(2*time.Second),
    )

    // Use client...
    // Использовать клиент...
}
```

### Functional Options Pattern (Паттерн функциональных опций)

```go
// Available options / Доступные опции:
client := sattva.NewClient(
    apiKey,
    sattva.WithBaseURL("https://custom.api.com/v1"),
    sattva.WithTimeout(60 * time.Second),
    sattva.WithMaxRetries(10),
    sattva.WithRetryDelay(5 * time.Second),
)
```

### Concurrent Requests (Конкурентные запросы)

```go
package main

import (
    "context"
    "sync"
    "log"

    "github.com/sattva/sattva-go-sdk"
)

func main() {
    client := sattva.NewClient("your-api-key")
    ctx := context.Background()

    // Make concurrent requests / Делать конкурентные запросы
    var wg sync.WaitGroup
    streamIDs := []string{"stream-1", "stream-2", "stream-3"}

    for _, id := range streamIDs {
        wg.Add(1)
        go func(streamID string) {
            defer wg.Done()

            stream, err := client.Streams.Get(ctx, streamID)
            if err != nil {
                log.Printf("Error getting %s: %v", streamID, err)
                return
            }

            log.Printf("Stream %s: %s\n", streamID, stream.Name)
        }(id)
    }

    wg.Wait()
}
```

## Testing (Тестирование)

### Table-Driven Tests (Тесты с таблицами)

```go
package main

import (
    "context"
    "testing"

    "github.com/sattva/sattva-go-sdk"
)

func TestStreamsList(t *testing.T) {
    client := sattva.NewClient("test-api-key")
    ctx := context.Background()

    streams, err := client.Streams.List(ctx)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if streams == nil {
        t.Error("expected streams to not be nil")
    }
}

func TestStreamsGet(t *testing.T) {
    tests := []struct {
        name     string
        streamID string
        wantErr  bool
    }{
        {
            name:     "valid stream",
            streamID: "stream-123",
            wantErr:  false,
        },
        {
            name:     "invalid stream",
            streamID: "invalid-id",
            wantErr:  true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            client := sattva.NewClient("test-api-key")
            ctx := context.Background()

            _, err := client.Streams.Get(ctx, tt.streamID)
            if (err != nil) != tt.wantErr {
                t.Errorf("Streams.Get() error = %v, wantErr %v", err, tt.wantErr)
            }
        })
    }
}
```

### Mocking (Мокинг)

```go
// Create mock interface / Создать mock интерфейс
type MockStreamsService struct {
    ListFunc func(ctx context.Context) ([]sattva.Stream, error)
    GetFunc  func(ctx context.Context, id string) (*sattva.Stream, error)
}

func (m *MockStreamsService) List(ctx context.Context) ([]sattva.Stream, error) {
    if m.ListFunc != nil {
        return m.ListFunc(ctx)
    }
    return []sattva.Stream{}, nil
}

func (m *MockStreamsService) Get(ctx context.Context, id string) (*sattva.Stream, error) {
    if m.GetFunc != nil {
        return m.GetFunc(ctx, id)
    }
    return &sattva.Stream{ID: id}, nil
}
```

## Development (Разработка)

### Running Tests (Запуск тестов)

```bash
# Run all tests / Запустить все тесты
go test ./...

# Run tests with verbose output / Запустить тесты с подробным выводом
go test ./... -v

# Run tests with coverage / Запустить тесты с покрытием
go test ./... -cover -coverprofile=coverage.out

# View coverage report / Просмотреть отчет покрытия
go tool cover -html=coverage.out
```

### Code Quality (Качество кода)

```bash
# Format code / Форматировать код
go fmt ./...

# Vet code / Проверить код
go vet ./...

# Run linters / Запустить линтеры
golangci-lint run
```

### Building (Сборка)

```bash
# Build for current platform / Собрать для текущей платформы
go build

# Build for multiple platforms / Собрать для множества платформ
GOOS=linux GOARCH=amd64 go build -o sattva-linux-amd64
GOOS=windows GOARCH=amd64 go build -o sattva-windows-amd64.exe
GOOS=darwin GOARCH=amd64 go build -o sattva-darwin-amd64
GOOS=darwin GOARCH=arm64 go build -o sattva-darwin-arm64
```

## Event Types (Типы событий)

Webhook events available for subscription / Вебхук-события, доступные для подписки:

| Event Type | Description / Описание |
|------------|----------------------|
| `stream.started` | Stream has started / Стрим запущен |
| `stream.stopped` | Stream has stopped / Стрим остановлен |
| `stream.paused` | Stream has been paused / Стрим на паузе |
| `stream.resumed` | Stream has been resumed / Стрим возобновлен |
| `stream.error` | Stream encountered an error / Ошибка стрима |
| `viewer.milestone` | Viewer milestone reached / Достигнут milestone зрителей |
| `viewer.joined` | Viewer joined the stream / Зритель присоединился |
| `viewer.left` | Viewer left the stream / Зритель покинул стрим |
| `track.started` | Track started playing / Трек начал воспроизводиться |
| `track.completed` | Track finished playing / Трек закончил воспроизводиться |
| `track.failed` | Track failed to play / Трек не воспроизвелся |
| `track.skipped` | Track was skipped / Трек пропущен |

## Common Use Cases (Частые случаи использования)

### CLI Application (CLI приложение)

```go
package main

import (
    "context"
    "flag"
    "fmt"
    "log"
    "os"

    "github.com/sattva/sattva-go-sdk"
)

func main() {
    apiKey := flag.String("api-key", "", "Sattva API key")
    action := flag.String("action", "list", "Action to perform")
    flag.Parse()

    if *apiKey == "" {
        *apiKey = os.Getenv("SATTVA_API_KEY")
    }

    client := sattva.NewClient(*apiKey)
    ctx := context.Background()

    switch *action {
    case "list":
        streams, err := client.Streams.List(ctx)
        if err != nil {
            log.Fatal(err)
        }
        for _, stream := range streams {
            fmt.Printf("%s: %s\n", stream.ID, stream.Name)
        }
    case "start":
        // Start stream logic / Логика запуска стрима
    }
}
```

### REST API Wrapper (REST API обертка)

```go
package main

import (
    "context"
    "encoding/json"
    "log"
    "net/http"

    "github.com/gorilla/mux"
    "github.com/sattva/sattva-go-sdk"
)

type Server struct {
    client *sattva.Client
}

func (s *Server) listStreams(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()

    streams, err := s.client.Streams.List(ctx)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

    json.NewEncoder(w).Encode(streams)
}

func main() {
    client := sattva.NewClient(os.Getenv("SATTVA_API_KEY"))
    server := &Server{client: client}

    r := mux.NewRouter()
    r.HandleFunc("/streams", server.listStreams).Methods("GET")

    log.Println("Server starting on :8080")
    log.Fatal(http.ListenAndServe(":8080", r))
}
```

### Background Worker (Фоновый воркер)

```go
package main

import (
    "context"
    "log"
    "time"

    "github.com/sattva/sattva-go-sdk"
)

func monitorStreams(ctx context.Context, client *sattva.Client) {
    ticker := time.NewTicker(30 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            streams, err := client.Streams.List(ctx)
            if err != nil {
                log.Printf("Error listing streams: %v", err)
                continue
            }

            for _, stream := range streams {
                if stream.Status == "error" {
                    log.Printf("Stream %s has errors, restarting...\n", stream.ID)
                    _, err := client.Streams.Restart(ctx, stream.ChannelID)
                    if err != nil {
                        log.Printf("Error restarting stream: %v\n", err)
                    }
                }
            }
        }
    }
}

func main() {
    client := sattva.NewClient("your-api-key")
    ctx := context.Background()

    monitorStreams(ctx, client)
}
```

## Troubleshooting (Решение проблем)

### Common Issues (Частые проблемы)

| Problem / Проблема | Solution / Решение |
|-------------------|-------------------|
| Context deadline exceeded | Increase timeout value / Увеличьте значение таймаута |
| Authentication error | Check API key validity / Проверьте валидность API ключа |
| Rate limit errors | SDK auto-retries, but consider reducing request frequency / SDK автоматически повторяет, но рассмотрите уменьшение частоты запросов |
| Connection refused | Check network connectivity and firewall / Проверьте сетевое подключение и firewall |

### Debug Logging (Debug-логирование)

```go
import "log"

// Set debug mode / Включить debug режим
client := sattva.NewClient(
    "your-api-key",
    sattva.WithDebug(true),  // Enables request/response logging
                             // Включает логирование запросов/ответов
)
```

## Related Documents (Связанные документы)

- [API Reference](./reference.md)
- [Authentication Guide](./authentication.md)
- [Webhooks Guide](./webhooks.md)
- [API Versioning](./versioning.md)
- [026 Spec](../../specs/026-api-webhook-ecosystem/)

## Support & Resources (Поддержка и ресурсы)

- **Documentation / Документация**: [https://docs.sattva.io](https://docs.sattva.io)
- **GitHub / GitHub**: [https://github.com/sattva/sattva-go-sdk](https://github.com/sattva/sattva-go-sdk)
- **GoDoc / GoDoc**: [https://pkg.go.dev/github.com/sattva/sattva-go-sdk](https://pkg.go.dev/github.com/sattva/sattva-go-sdk)
- **Bug Reports / Баг-репорты**: [GitHub Issues](https://github.com/sattva/sattva-go-sdk/issues)
- **Email / Email**: api@sattva.io

## License (Лицензия)

MIT License - see LICENSE file for details / см. файл LICENSE для деталей
