# Архитектура проекта (C4 Model)

**Версия документа**: 1.0
**Дата создания**: 26.11.2025

## 1. System Context Diagram (Уровень 1)

Диаграмма контекста показывает, как система взаимодействует с внешним миром.

```mermaid
C4Context
    title System Context Diagram for Telegram Video Streamer

    Person(admin, "Administrator", "Manages users, playlists, and stream settings")
    Person(user, "User", "Views dashboard and stream status")
    Person(guest, "Guest", "Registers and requests access")

    System(streamer_system, "Telegram Video Streamer", "24/7 TV Streaming System")

    System_Ext(telegram, "Telegram", "Video Chat Platform")
    System_Ext(youtube, "YouTube", "Content Source")
    System_Ext(google, "Google OAuth", "Authentication Provider")
    System_Ext(smtp, "SMTP Server", "Email Notifications")

    Rel(admin, streamer_system, "Manages", "HTTPS")
    Rel(user, streamer_system, "Views status", "HTTPS")
    Rel(guest, streamer_system, "Registers", "HTTPS")

    Rel(streamer_system, telegram, "Streams Video/Audio", "MTProto/WebRTC")
    Rel(streamer_system, youtube, "Downloads Content", "HTTPS")
    Rel(streamer_system, google, "Authenticates Users", "OIDC")
    Rel(streamer_system, smtp, "Sends Emails", "SMTP")
```

## 2. Container Diagram (Уровень 2)

Диаграмма контейнеров показывает основные приложения и сервисы.

```mermaid
C4Container
    title Container Diagram for Telegram Video Streamer

    Person(admin, "Administrator", "Manages system")
    Person(user, "User", "Views status")

    System_Ext(telegram, "Telegram", "Video Chat")
    System_Ext(youtube, "YouTube", "Content Source")

    Container_Boundary(c1, "Telegram Video Streamer") {
        Container(frontend, "Frontend App", "React, Vite", "Web Dashboard for management")
        Container(backend, "Backend API", "FastAPI, Python", "Business logic, Auth, Playlist management")
        Container(streamer, "Streamer Service", "Python, PyTgCalls", "Handles video streaming to Telegram")
        ContainerDb(db, "Database", "PostgreSQL", "Stores users, playlists, settings")
        ContainerDb(redis, "Cache/Broker", "Redis", "Session storage, Caching")
    }

    Rel(admin, frontend, "Uses", "HTTPS")
    Rel(user, frontend, "Uses", "HTTPS")

    Rel(frontend, backend, "API Calls", "JSON/HTTPS")
    
    Rel(backend, db, "Reads/Writes", "SQL/TCP")
    Rel(backend, redis, "Caches data", "RESP/TCP")

    Rel(streamer, backend, "Fetches Playlist", "JSON/HTTP")
    Rel(streamer, youtube, "Downloads Video", "HTTPS")
    Rel(streamer, telegram, "Streams Content", "MTProto")
    Rel(streamer, redis, "Uses (optional)", "RESP/TCP")
```

## 3. Component Diagram - Backend (Уровень 3)

Детализация Backend API.

```mermaid
C4Component
    title Component Diagram - Backend API

    Container(frontend, "Frontend App", "React", "Web Client")
    ContainerDb(db, "Database", "PostgreSQL", "Data Store")

    Container_Boundary(api, "Backend API") {
        Component(auth_route, "Auth Controller", "FastAPI Router", "Handles Login, Register, OAuth")
        Component(playlist_route, "Playlist Controller", "FastAPI Router", "Manage Playlists")
        Component(users_route, "Users Controller", "FastAPI Router", "Manage Users")
        Component(admin_route, "Admin Controller", "FastAPI Router", "Admin specific operations")
        
        Component(auth_service, "Auth Service", "Service Layer", "Business logic for Auth")
        Component(models, "ORM Models", "SQLAlchemy", "User, Playlist entities")
    }

    Rel(frontend, auth_route, "POST /login, /register")
    Rel(frontend, playlist_route, "GET/POST /playlist")
    Rel(frontend, admin_route, "GET/POST /admin")

    Rel(auth_route, auth_service, "Uses")
    Rel(auth_service, models, "Uses")
    Rel(playlist_route, models, "Uses")
    
    Rel(models, db, "Persists data")
```

## 4. Component Diagram - Streamer (Уровень 3)

Детализация сервиса стриминга.

```mermaid
C4Component
    title Component Diagram - Streamer Service

    Container(backend, "Backend API", "FastAPI", "Playlist Source")
    System_Ext(telegram, "Telegram", "Target Platform")

    Container_Boundary(streamer, "Streamer Service") {
        Component(main_loop, "Main Loop", "Python AsyncIO", "Orchestrates playback")
        Component(playlist_mgr, "Playlist Manager", "Utils", "Fetches and expands playlists")
        Component(tg_client, "Telegram Client", "Pyrogram", "Manages Telegram Session")
        Component(stream_engine, "Streaming Engine", "PyTgCalls", "Wraps FFmpeg and WebRTC")
        Component(metrics, "Metrics Server", "Prometheus Client", "Exposes metrics")
    }

    Rel(main_loop, playlist_mgr, "Gets next track")
    Rel(playlist_mgr, backend, "Fetches JSON")
    
    Rel(main_loop, tg_client, "Ensures connection")
    Rel(main_loop, stream_engine, "Commands play/stop")
    
    Rel(stream_engine, telegram, "Streams Media")
    Rel(metrics, main_loop, "Monitors activity")
```
