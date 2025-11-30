# Docker Network Architecture

**Дата создания**: 29.11.2025  
**Ветка**: 012-project-improvements  
**User Story**: US-1 (Security)

## Обзор

Проект использует изолированные Docker networks для обеспечения безопасности
и разделения трафика между сервисами.

## Топология сетей

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            EXTERNAL NETWORK                              │
│                         (доступ извне, bridge)                           │
│                                                                          │
│   ┌──────────────┐              ┌──────────────┐                        │
│   │   frontend   │─────────────►│   backend    │                        │
│   │    :3000     │   /api/*     │    :8000     │                        │
│   └──────────────┘              └──────┬───────┘                        │
│                                        │                                 │
└────────────────────────────────────────┼─────────────────────────────────┘
                                         │
                                         │ (также в internal)
                                         │
┌────────────────────────────────────────┼─────────────────────────────────┐
│                            INTERNAL NETWORK                              │
│                    (изолированная, internal: true)                       │
│                                        │                                 │
│   ┌──────────┐              ┌──────────▼───────┐              ┌────────┐│
│   │    db    │◄─────────────┤     backend      ├─────────────►│ redis  ││
│   │  :5432   │              │      :8000       │              │ :6379  ││
│   └──────────┘              └──────────────────┘              └────┬───┘│
│                                                                    │    │
└────────────────────────────────────────────────────────────────────┼────┘
                                                                     │
                                                                     │ (также в streamer)
                                                                     │
┌────────────────────────────────────────────────────────────────────┼────┐
│                           STREAMER NETWORK                         │    │
│                         (изолированная, bridge)                    │    │
│                                                                    │    │
│   ┌────────────────┐                                         ┌─────▼──┐ │
│   │    streamer    │─────────────────────────────────────────│ redis  │ │
│   │                │         Queue/Messages                  │ :6379  │ │
│   └────────────────┘                                         └────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Описание сетей

### External Network
- **Тип**: bridge (стандартный)
- **Назначение**: Внешний доступ к frontend и backend API
- **Сервисы**: frontend, backend
- **Доступ**: Открыт на порты 3000, 8000

### Internal Network  
- **Тип**: bridge с `internal: true`
- **Назначение**: Изолированная сеть для БД и кэша
- **Сервисы**: backend, db, redis
- **Особенность**: Нет маршрутизации наружу (internal: true)

### Streamer Network
- **Тип**: bridge
- **Назначение**: Изоляция стриминг-сервиса
- **Сервисы**: streamer, redis
- **Особенность**: Redis доступен для очередей задач

## Принципы безопасности

### 1. Минимальные привилегии
- База данных недоступна напрямую извне
- Frontend не имеет доступа к internal network
- Streamer изолирован от backend и БД

### 2. Defense in Depth
- Несколько уровней сетевой изоляции
- Health checks для мониторинга состояния
- Отсутствие Docker socket mount

### 3. Credentials Security
- PostgreSQL пароль через переменную `${DB_PASSWORD}`
- Все секреты в `.env` файлах (не в docker-compose.yml)
- `.env` файлы в `.gitignore`

## Конфигурация Docker Compose

```yaml
networks:
  external:
    driver: bridge
  internal:
    driver: bridge
    internal: true  # Блокирует внешний трафик
  streamer:
    driver: bridge

services:
  backend:
    networks:
      - external
      - internal
  
  frontend:
    networks:
      - external
  
  db:
    networks:
      - internal
  
  redis:
    networks:
      - internal
      - streamer
  
  streamer:
    networks:
      - streamer
```

## Миграция с предыдущей версии

До изменений все сервисы находились в default network:

```yaml
# Было (небезопасно):
services:
  backend:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # УДАЛЕНО
  db:
    environment:
      - POSTGRES_PASSWORD=postgres  # ИЗМЕНЕНО на ${DB_PASSWORD}
```

### Шаги миграции:
1. Добавить `DB_PASSWORD` в `.env`
2. Обновить `docker-compose.yml` с новыми сетями
3. Перезапустить: `docker compose down && docker compose up -d`

## Валидация

Запустите smoke test для проверки конфигурации:

```bash
./tests/smoke/test_security_docker.sh
```

Ожидаемый результат:
```
[1/4] Проверка Docker socket mount... ✅ PASS
[2/4] Проверка hardcoded credentials... ✅ PASS
[3/4] Проверка сетевой изоляции... ✅ PASS
[4/4] Проверка Trivy security scan... ✅ PASS
```

## См. также

- [C4 Diagrams](./C4_DIAGRAMS.md) — архитектурные диаграммы
- [Security Audit](../../PROJECT_AUDIT_REPORT.md) — полный аудит безопасности
