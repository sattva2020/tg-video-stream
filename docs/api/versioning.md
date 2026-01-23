# API Versioning

> **Spec**: 026-api-webhook-ecosystem
> **Версия**: 1.0
> **Дата**: 2025-01-23

## Обзор

API versioning system для обеспечения обратной совместимости и плавного мигрования между версиями.
Поддержка множественных версий API с автоматическим определением версии из URL path или HTTP header.

**Ключевые возможности:**
- URL-based versioning (`/api/v1/`, `/api/v2/`)
- Header-based versioning (`X-API-Version`)
- Automatic version detection with fallback
- Version deprecation warnings
- Sunset dates for deprecated versions
- Migration guides between versions

## Версии API

| Версия | Статус | Релиз | Sunset | Описание |
|--------|--------|-------|--------|----------|
| **v1** | Stable | 2024-01-01 | — | Initial API release with basic functionality |
| **v2** | Beta | 2025-01-23 | — | Enhanced version with improved error handling and validation |

### Статусы версий

- **Stable**: Рекомендуемая версия для production использования
- **Beta**: Экспериментальная версия для тестирования новых возможностей
- **Deprecated**: Устаревшая версия, будет отключена в будущем

## Способы указания версии

### 1. URL Path (Рекомендуется)

Версия указывается в URL path после `/api/`:

```http
GET /api/v1/streams HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

```http
GET /api/v2/streams HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

**Приоритет:** URL path имеет высший приоритет при определении версии.

### 2. HTTP Header

Версия указывается через заголовок `X-API-Version`:

```http
GET /api/streams HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
X-API-Version: v1
```

**Приоритет:** Используется если версия не указана в URL path.

### 3. Default

Если версия не указана ни в URL ни в header, используется `v1`:

```http
GET /api/streams HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
# Будет использована версия v1
```

## Endpoints

### GET /api/version

Получить информацию о текущей версии API.

#### Request

```http
GET /api/version HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

#### Response

```json
{
  "current_version": "v1",
  "supported_versions": ["v1", "v2"],
  "deprecated_versions": [],
  "default_version": "v1",
  "documentation": {
    "v1": "/docs/v1",
    "v2": "/docs/v2"
  }
}
```

#### Поля ответа

| Поле | Тип | Описание |
|------|-----|----------|
| `current_version` | string | Текущая версия API |
| `supported_versions` | array | Список поддерживаемых версий |
| `deprecated_versions` | array | Список устаревших версий |
| `default_version` | string | Версия по умолчанию |
| `documentation` | object | Ссылки на документацию для каждой версии |

### GET /api/versions

Получить список всех версий API с описанием изменений.

#### Request

```http
GET /api/versions HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

#### Response

```json
{
  "versions": [
    {
      "version": "v1",
      "status": "stable",
      "released": "2024-01-01",
      "deprecated": false,
      "sunset_date": null,
      "features": [
        "API Keys authentication",
        "Webhooks",
        "Stream management",
        "Playlist management"
      ]
    },
    {
      "version": "v2",
      "status": "beta",
      "released": "2025-01-23",
      "deprecated": false,
      "sunset_date": null,
      "features": [
        "Everything in v1",
        "Improved error handling",
        "Request/response validation",
        "Rate limiting per API key",
        "Webhook delivery guarantees"
      ]
    }
  ]
}
```

## Version Headers

API автоматически добавляет заголовки версии ко всем ответам:

### X-API-Version

Текущая версия API для запроса.

```http
HTTP/1.1 200 OK
X-API-Version: v1
```

### X-API-Deprecated

Предупреждение если версия устарела.

```http
HTTP/1.1 200 OK
X-API-Version: v1
X-API-Deprecated: true
```

### X-API-Sunset

Дата отключения устаревшей версии (ISO 8601).

```http
HTTP/1.1 200 OK
X-API-Version: v1
X-API-Deprecated: true
X-API-Sunset: 2025-12-31
```

### X-API-Docs

Ссылка на документацию для текущей версии.

```http
HTTP/1.1 200 OK
X-API-Version: v1
X-API-Docs: /docs/v1
```

### X-API-Supported-Versions

Список всех поддерживаемых версий.

```http
HTTP/1.1 200 OK
X-API-Version: v1
X-API-Supported-Versions: v1, v2
```

## Пример использования (Python)

### Запрос с указанием версии в URL

```python
import requests

# API v1
response = requests.get(
    "https://api.example.com/api/v1/streams",
    headers={"Authorization": "Bearer <token>"}
)

# API v2
response = requests.get(
    "https://api.example.com/api/v2/streams",
    headers={"Authorization": "Bearer <token>"}
}
```

### Запрос с указанием версии в header

```python
import requests

response = requests.get(
    "https://api.example.com/api/streams",
    headers={
        "Authorization": "Bearer <token>",
        "X-API-Version": "v2"
    }
)

# Проверить версию ответа
version = response.headers.get("X-API-Version")
print(f"API Version: {version}")
```

### Проверка статуса версии

```python
import requests

# Получить информацию о версии
response = requests.get(
    "https://api.example.com/api/versions",
    headers={"Authorization": "Bearer <token>"}
)

versions = response.json()
for v in versions["versions"]:
    print(f"Version {v['version']}: {v['status']}")
    if v["deprecated"]:
        print(f"  ⚠️  Sunset date: {v['sunset_date']}")
```

## Пример использования (JavaScript/TypeScript)

### Запрос с указанием версии

```typescript
// API v1
const responseV1 = await fetch('https://api.example.com/api/v1/streams', {
  headers: {
    'Authorization': 'Bearer <token>'
  }
});

// API v2
const responseV2 = await fetch('https://api.example.com/api/v2/streams', {
  headers: {
    'Authorization': 'Bearer <token>'
  }
});

// Проверить версию ответа
const version = responseV1.headers.get('X-API-Version');
console.log(`API Version: ${version}`);
```

### Обработка deprecated версий

```typescript
async function makeRequest(url: string, options: RequestInit) {
  const response = await fetch(url, options);

  // Проверить deprecated статус
  const isDeprecated = response.headers.get('X-API-Deprecated') === 'true';
  if (isDeprecated) {
    const sunsetDate = response.headers.get('X-API-Sunset');
    console.warn(`⚠️  API version is deprecated. Sunset: ${sunsetDate}`);
    const migrationGuide = response.headers.get('X-API-Migration-Guide');
    if (migrationGuide) {
      console.log(`Migration guide: ${migrationGuide}`);
    }
  }

  return response;
}
```

## Политика Deprecation

### Процесс объявления версии устаревшей

1. **Announcement**: За 6 месяцев до отключения версия помечается как `deprecated`
2. **Warning**: Все ответы включают `X-API-Deprecated: true` header
3. **Sunset Date**: Указывается дата отключения в `X-API-Sunset` header
4. **Migration Guide**: Предоставляется руководство по миграции на новую версию
5. **Shutdown**: В sunset_date версия перестает поддерживаться

### Пример уведомления о deprecation

```http
HTTP/1.1 200 OK
X-API-Version: v1
X-API-Deprecated: true
X-API-Sunset: 2025-12-31
X-API-Migration-Guide: https://docs.example.com/migration/v1-to-v2
```

## Migration Guides

### Migration from v1 to v2

Изменения в v2:

1. **Enhanced Validation**
   - Strict request validation
   - Detailed error messages
   - Field-level error descriptions

2. **Improved Error Handling**
   - Consistent error response format
   - HTTP status codes follow RFC 9110
   - Error codes for programmatic handling

3. **Rate Limiting**
   - Per-API-key rate limits
   - Rate limit info in response headers
   - Retry-After header on 429 responses

4. **Breaking Changes**
   - None (v2 is backward compatible)
   - Additive changes only

#### Пример миграции

**v1 Request:**
```http
POST /api/v1/streams HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Stream"
}
```

**v2 Request (same format):**
```http
POST /api/v2/streams HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Stream"
}
```

**v2 Response (enhanced):**
```http
HTTP/1.1 201 Created
X-API-Version: v2
X-RateLimit-Remaining: 99

{
  "id": "123",
  "name": "My Stream",
  "status": "active",
  "created_at": "2025-01-23T10:00:00Z",
  "updated_at": "2025-01-23T10:00:00Z"
}
```

## Реализация

### Backend

- **Versioning System**: `backend/src/frameworks/http/versioning.py`
- **Middleware**: `backend/src/frameworks/http/middleware/version_headers.py`
- **Router Registration**: `backend/src/frameworks/http/app.py`

### Version Detection Logic

```python
def get_api_version(request: Request) -> APIVersion:
    """
    Определить версию API из запроса.

    Приоритет:
    1. URL path (/api/v1/, /api/v2/)
    2. Header X-API-Version
    3. Default (v1)
    """
    # 1. Проверяем URL path
    path_version = extract_version_from_path(request.url.path)
    if path_version:
        return APIVersion(path_version)

    # 2. Проверяем заголовок
    header_version = extract_version_from_header(request.headers)
    if header_version:
        return APIVersion(header_version)

    # 3. Default
    return APIVersion.V1
```

### Version Routers

```python
# v1 endpoints
v1_router = APIRouter(prefix="/v1", tags=["API v1"])

# v2 endpoints
v2_router = APIRouter(prefix="/v2", tags=["API v2"])

# Version info endpoints
version_router = APIRouter(prefix="/api", tags=["API Versioning"])
```

## Best Practices

### Для разработчиков клиентов

1. **Явно указывайте версию** в URL path (не полагайтесь на default)
2. **Обрабатывайте deprecation warnings** из response headers
3. **Планируйте миграцию** заранее при получении deprecation уведомления
4. **Используйте `/api/versions` endpoint** для проверки статуса версии
5. **Логируйте изменения версии** для мониторинга

### Пример robust клиента

```python
class APIClient:
    def __init__(self, api_key: str, version: str = "v1"):
        self.api_key = api_key
        self.version = version
        self.base_url = "https://api.example.com/api"
        self.session = requests.Session()

    def request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.base_url}/{self.version}/{endpoint}"
        response = self.session.request(
            method,
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            **kwargs
        )

        # Check deprecation
        if response.headers.get("X-API-Deprecated") == "true":
            sunset = response.headers.get("X-API-Sunset")
            self.logger.warning(
                f"API {self.version} deprecated. Sunset: {sunset}"
            )

        return response
```

## Troubleshooting

### Ошибка: Unsupported API version

```json
{
  "detail": "Unsupported API version: v3"
}
```

**Решение:** Используйте одну из поддерживаемых версий: v1, v2

### Версия определяется неверно

**Проблема:** Version в header игнорируется при наличии версии в URL.

**Решение:** URL path имеет приоритет над header. Используйте один способ.

### Missing version headers

**Проблема:** Response не содержит `X-API-Version` header.

**Решение:** Убедитесь что запрос к `/api/*` endpoint, а не к `/health` или `/metrics`.

## Связанные документы

- [API Keys Authentication](./authentication.md)
- [Webhooks API](./webhooks.md)
- [Rate Limiting](./rate-limiting.md)
- [Activity Events API](./activity-events.md)
- [026-api-webhook-ecosystem Spec](../../specs/026-api-webhook-ecosystem/)
