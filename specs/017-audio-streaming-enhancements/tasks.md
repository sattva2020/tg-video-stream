# Tasks: Audio Streaming Enhancements

**Feature**: 017-audio-streaming-enhancements  
**Priority**: P1-P3  
**Generated**: 2025-01-26  
**Total Tasks**: 82  

---

## Phase 1: Setup

**Goal**: Initialize project structure and install dependencies

- [x] T001 [P] Install backend dependencies: `lyricsgenius`, `shazamio`, `APScheduler` in backend/requirements.txt
- [x] T002 [P] Install frontend dependencies: `react-i18next`, `i18next` in frontend/package.json
- [x] T003 [P] Create backend/src/services/__init__.py with service exports
- [x] T004 [P] Create backend/src/middleware/__init__.py with middleware exports
- [x] T005 [P] Create frontend/src/i18n/locales/ directory structure

**Checkpoint**: Dependencies installed, directory structure ready

---

## Phase 2: User Story 4 - Rate Limiting (Foundational, BLOCKS ALL)

**Goal**: Implement rate limiting infrastructure used by all subsequent features

**Why First**: Rate limiting (US4/FR-006/FR-007) protects all API endpoints from abuse

- [x] T006 [US4] Implement Fixed Window Counter rate limiter in backend/src/middleware/rate_limiter.py
- [x] T007 [US4] Add Redis INCR+EXPIRE pattern for rate tracking in backend/src/middleware/rate_limiter.py
- [x] T008 [US4] Create rate limit configuration schema in backend/src/config/rate_limits.py
- [x] T009 [US4] Add rate limit middleware to FastAPI app in backend/src/main.py
- [x] T010 [US4] Add 429 Too Many Requests response handler in backend/src/middleware/rate_limiter.py

**Checkpoint**: Rate limiting protects all endpoints, ready for feature development

---

## Phase 3: User Story 1 - Speed/Pitch Control (Priority: P1)

**Goal**: DJ может изменять скорость воспроизведения (0.5x-2.0x) и высоту тона для микширования

**Independent Test**: 
1. Start playback via Telegram
2. Send `/speed 1.5` command
3. Verify audio plays at 1.5x speed
4. Send `/pitch +2` command  
5. Verify pitch shifts up 2 semitones

### Implementation for User Story 1

- [x] T011 [P] [US1] Create PlaybackSettings model in backend/src/models/playback_settings.py
- [x] T012 [P] [US1] Create Alembic migration for playback_settings table in backend/alembic/versions/
- [x] T013 [US1] Implement PlaybackService with speed/pitch logic in backend/src/services/playback_service.py
- [x] T014 [US1] Integrate GStreamer scaletempo plugin in streamer/playback_control.py
- [x] T015 [US1] Add `/speed {value}` Telegram command handler in backend/src/telegram/commands/playback.py
- [x] T016 [US1] Add `/pitch {semitones}` Telegram command handler in backend/src/telegram/commands/playback.py
- [x] T017 [US1] Create PUT /api/playback/speed endpoint in backend/src/api/routes/playback.py
- [x] T018 [US1] Create PUT /api/playback/pitch endpoint in backend/src/api/routes/playback.py
- [x] T019 [P] [US1] Create SpeedControl React component in frontend/src/components/player/SpeedControl.tsx

**Checkpoint**: Speed/pitch control fully functional via Telegram and Web UI

---

## Phase 4: User Story 2 - Seek & Rewind (Priority: P1)

**Goal**: Слушатель может перемотать трек на определённое время или позицию

**Independent Test**:
1. Start playback of 3+ minute track
2. Send `/seek 1:30` command
3. Verify playback jumps to 1:30 position
4. Click seek bar at 50% position in Web UI
5. Verify playback jumps to middle of track

### Implementation for User Story 2

- [x] T020 [US2] Implement seek logic in PlaybackService in backend/src/services/playback_service.py
- [x] T021 [US2] Add PyTgCalls seek_stream integration in streamer/playback_control.py
- [x] T022 [US2] Add `/seek {time}` Telegram command handler in backend/src/telegram/commands/playback.py
- [x] T023 [US2] Add `/forward {seconds}` and `/rewind {seconds}` commands in backend/src/telegram/commands/playback.py
- [x] T024 [US2] Create POST /api/playback/seek endpoint in backend/src/api/routes/playback.py
- [x] T025 [US2] Create GET /api/playback/position endpoint in backend/src/api/routes/playback.py
- [x] T026 [P] [US2] Create SeekBar React component with progress display in frontend/src/components/player/SeekBar.tsx

**Checkpoint**: Seek/rewind functional via Telegram and Web UI with position tracking

---

## Phase 5: User Story 3 - Radio Streams (Priority: P1)

**Goal**: Администратор может добавлять и воспроизводить интернет-радиостанции

**Independent Test**:
1. Add radio stream via `/addradio {url} {name}`
2. Send `/radio {name}` command
3. Verify HTTP stream plays continuously
4. Verify stream reconnects on network interruption

### Implementation for User Story 3

- [x] T027 [P] [US3] Create RadioStream model in backend/src/models/radio_stream.py
- [x] T028 [P] [US3] Create Alembic migration for radio_streams table in backend/alembic/versions/
- [x] T029 [US3] Implement RadioService with URL validation in backend/src/services/radio_service.py
- [x] T030 [US3] Add HTTP stream handler in streamer/radio_handler.py
- [x] T031 [US3] Add `/addradio {url} {name}` Telegram command in backend/src/telegram/commands/radio.py
- [x] T032 [US3] Add `/radio {name}` and `/radiolist` commands in backend/src/telegram/commands/radio.py
- [x] T033 [US3] Create POST /api/radio/streams endpoint in backend/src/api/routes/radio.py
- [x] T034 [US3] Create GET /api/radio/streams endpoint in backend/src/api/routes/radio.py

**Checkpoint**: Radio streams can be added, listed, and played

---

## Phase 6: User Story 5 - Priority Queues (Priority: P2)

**Goal**: VIP пользователи получают приоритет в очереди воспроизведения

**Independent Test**:
1. Add 3 tracks as regular user
2. Add 1 track as VIP user
3. Verify VIP track moves ahead in queue
4. Verify priority preserved after restart

### Implementation for User Story 4

- [x] T035 [US5] Implement PriorityQueueService with Redis sorted sets in backend/src/services/queue_service.py
- [x] T036 [US5] Add user role detection for priority scoring in backend/src/services/queue_service.py
- [x] T037 [US5] Integrate priority queue with existing queue system in backend/src/services/queue_service.py
- [x] T038 [US5] Add `/vipqueue` command for VIP users in backend/src/telegram/commands/queue.py
- [x] T039 [US5] Update queue display to show priority indicators in backend/src/telegram/commands/queue.py

**Checkpoint**: VIP priority queue working, visible priority indicators

---

## Phase 7: User Story 6 - Equalizer (Priority: P2)

**Goal**: DJ может применять предустановки эквалайзера (Bass Boost, Vocal, Meditation, Relax, etc.)

**Independent Test**:
1. Start playback
2. Send `/eq bassboost` command
3. Verify bass frequencies are boosted
4. Select "Vocal" preset in Web UI
5. Verify mid frequencies enhanced

### Implementation for User Story 5

- [x] T040 [US6] Add equalizer presets configuration (12 presets incl. meditation, relax) in backend/src/config/equalizer_presets.py
- [x] T041 [US6] Implement GStreamer equalizer-10bands integration in streamer/audio_filters.py
- [x] T042 [US6] Add `/eq {preset}` Telegram command in backend/src/telegram/commands/equalizer.py
- [x] T043 [US6] Create GET /api/playback/equalizer/presets endpoint in backend/src/api/routes/playback.py
- [x] T044 [US6] Create PUT /api/playback/equalizer endpoint in backend/src/api/routes/playback.py
- [x] T045 [P] [US6] Create EqualizerPanel React component in frontend/src/components/player/EqualizerPanel.tsx

**Checkpoint**: Equalizer presets work via Telegram and Web UI

---

## Phase 8: User Story 7 - Scheduled Playlists (Priority: P2)

**Goal**: Администратор может планировать автоматическое воспроизведение плейлистов

**Independent Test**:
1. Create schedule via `/schedule 08:00 morning_playlist`
2. Wait until 08:00 (or mock time)
3. Verify playlist starts automatically
4. Verify schedule persists across restarts

### Implementation for User Story 6

- [x] T046 [P] [US7] Create ScheduledPlaylist model in backend/src/models/scheduled_playlist.py
- [x] T047 [P] [US7] Create Alembic migration for scheduled_playlists table in backend/alembic/versions/
- [x] T048 [US7] Implement SchedulerService with APScheduler in backend/src/services/scheduler_service.py
- [x] T049 [US7] Add `/schedule {time} {playlist}` Telegram command in backend/src/telegram/commands/scheduler.py
- [x] T050 [US7] Add `/unschedule {id}` and `/schedules` commands in backend/src/telegram/commands/scheduler.py
- [x] T051 [US7] Create POST /api/scheduler/schedules endpoint in backend/src/api/routes/scheduler.py
- [x] T052 [US7] Create GET /api/scheduler/schedules endpoint in backend/src/api/routes/scheduler.py

**Checkpoint**: Scheduled playlists work, persist across restarts

---

## Phase 9: User Story 8 - Lyrics Display (Priority: P2)

**Goal**: Слушатель может видеть текст песни с синхронизацией

**Independent Test**:
1. Play track with lyrics available
2. Send `/lyrics` command
3. Verify lyrics retrieved from Genius API
4. Verify lyrics cached in database

### Implementation for User Story 7

- [x] T053 [P] [US8] Create LyricsCache model in backend/src/models/lyrics_cache.py
- [x] T054 [P] [US8] Create Alembic migration for lyrics_cache table in backend/alembic/versions/
- [x] T055 [US8] Implement LyricsService with Genius API integration in backend/src/services/lyrics_service.py
- [x] T056 [US8] Add caching logic with 7-day TTL in backend/src/services/lyrics_service.py
- [x] T057 [US8] Add `/lyrics` Telegram command in backend/src/telegram/commands/lyrics.py
- [x] T058 [US8] Create GET /api/lyrics/{track_id} endpoint in backend/src/api/routes/lyrics.py
- [x] T059 [P] [US8] Create LyricsDisplay React component in frontend/src/components/player/LyricsDisplay.tsx

**Checkpoint**: Lyrics display works with caching

---

## Phase 10: User Story 9 - Music Recognition (Priority: P3)

**Goal**: Пользователь может отправить аудио-сообщение и узнать название песни (Shazam)

**Independent Test**:
1. Send voice message or audio file to bot
2. Verify Shazam recognition returns track info
3. Verify recognition respects rate limits (10 req/min)

### Implementation for User Story 8

- [x] T060 [US9] Implement ShazamService with shazamio library in backend/src/services/shazam_service.py
- [x] T061 [US9] Add audio message handler in backend/src/telegram/handlers/audio_recognition.py
- [x] T062 [US9] Create POST /api/recognition/identify endpoint in backend/src/api/routes/recognition.py
- [x] T063 [US9] Add rate limiting (10 req/min) for recognition in backend/src/config/rate_limits.py

**Checkpoint**: Music recognition works via Telegram and API

---

## Phase 11: User Story 11 - Multi-channel Support (Priority: P3)

**Goal**: Администратор может управлять несколькими Telegram каналами одновременно

**Independent Test**:
1. Configure 2 Telegram channels
2. Start playback in channel 1
3. Verify channel 2 is independent
4. Apply different settings to each channel

### Implementation for User Story 9

- [x] T064 [US11] Add channel_id to PlaybackSettings model in backend/src/models/playback_settings.py
- [x] T065 [US11] Update PlaybackService for multi-channel isolation in backend/src/services/playback_service.py
- [x] T066 [US11] Add channel selection to Telegram commands in backend/src/telegram/commands/channel.py
- [x] T067 [US11] Update streamer for multiple concurrent streams in streamer/multi_channel.py

**Checkpoint**: Multiple channels work independently

---

## Phase 12: User Story 10 - Interface Localization (Priority: P3)

**Goal**: Интерфейс доступен на русском, украинском, английском и испанском

**Independent Test**:
1. Open Web UI, verify default language (ru)
2. Switch to English via language selector
3. Verify all UI strings translated
4. Verify preference persists in localStorage

### Implementation for User Story 10

- [x] T068 [P] [US10] Create translation files: ru.json, en.json, uk.json, es.json in frontend/src/i18n/locales/
- [x] T069 [US10] Configure react-i18next in frontend/src/i18n/index.ts
- [x] T070 [US10] Add LanguageSwitcher component in frontend/src/components/common/LanguageSwitcher.tsx
- [x] T071 [US10] Wrap App component with I18nextProvider in frontend/src/App.tsx
- [x] T072 [US10] Add Telegram language detection in backend/src/telegram/handlers/language.py
- [x] T073 [US10] Create GET /api/i18n/languages endpoint in backend/src/api/routes/i18n.py

**Checkpoint**: Full i18n support with 4 languages

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple user stories

- [x] T074 [P] Update API documentation in docs/api/audio-streaming.md
- [x] T075 [P] Add feature documentation in docs/features/audio-streaming-enhancements.md
- [x] T076 Code cleanup and refactoring across all new services
- [x] T077 Performance optimization for GStreamer pipelines
- [x] T078 Security review of rate limiting and input validation
- [x] T079 Run quickstart.md validation scenarios
- [x] T080 [P] Implement automated backups for configuration and data (FR-014) in backend/src/services/backup_service.py
- [x] T081 [P] Implement Grafana dashboards and instrumentation for audio-streaming metrics in infra/monitoring/grafana/
- [x] T082 [P] Integrate Sentry for error tracking and add monitoring hooks in backend/src/instrumentation/sentry.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS ALL USER STORIES**
- **User Stories (Phase 3-12)**: All depend on Foundational phase completion
- **Polish (Phase 13)**: Depends on all desired user stories being complete

### User Story Dependencies

| Story | Priority | Depends On | Can Parallelize With |
|-------|----------|------------|---------------------|
| US1 Speed/Pitch | P1 | Foundational (US4) | US2, US3 |
| US2 Seek/Rewind | P1 | Foundational (US4) | US1, US3 |
| US3 Radio | P1 | Foundational (US4) | US1, US2 |
| US4 Rate Limiting | P1 | Setup | BLOCKS ALL |
| US5 Priority Queues | P2 | Foundational (US4) | US6, US7 |
| US6 Equalizer | P2 | Foundational + US1 (PlaybackService) | US5, US7 |
| US7 Scheduler | P2 | Foundational (US4) | US5, US6, US8 |
| US8 Lyrics | P2 | Foundational (US4) | US6, US7, US9 |
| US9 Shazam | P3 | Foundational (US4) | US8, US10 |
| US10 i18n | P3 | Foundational (US4) | US9, US11 |
| US11 Multi-channel | P3 | US1, US3 (channel isolation) | US10 |

### Within Each User Story

- Models before services
- Services before endpoints/commands
- Backend before frontend components
- Core implementation before integration

### Parallel Opportunities

- **Phase 1**: All T001-T005 can run in parallel
- **Phase 3-6 (P1 stories)**: Can all start after Foundational completes
- **Phase 7-9 (P2 stories)**: Can start after P1 stories or in parallel
- **Frontend components**: All marked [P] can develop in parallel with backend

---

## Parallel Example: P1 User Stories

```bash
# After Foundational (Phase 2) completes, launch all P1 stories:

# Developer A: User Story 1 - Speed/Pitch
Task T011-T019

# Developer B: User Story 2 - Seek/Rewind  
Task T020-T026

# Developer C: User Story 3 - Radio Streams
Task T027-T034

# Developer D: User Story 4 - Priority Queues
Task T035-T039
```

---

## Implementation Strategy

### MVP First (P1 Stories Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: US4 Rate Limiting (Foundational)
3. Complete Phase 3: US1 Speed/Pitch → **Test independently**
4. Complete Phase 4: US2 Seek/Rewind → **Test independently**
5. Complete Phase 5: US3 Radio Streams → **Test independently**
6. Complete Phase 6: US5 Priority Queues → **Test independently**
7. **MVP COMPLETE** - Deploy core features

### Incremental Delivery

| Release | Stories | Value Delivered |
|---------|---------|-----------------|
| MVP | US1-4 | Core playback + rate limiting |
| v1.1 | +US5,6,7 | DJ tools (priority, equalizer, scheduler) |
| v1.2 | +US8,9 | Discovery (lyrics, Shazam) |
| v1.3 | +US10,11 | Scale (i18n, multi-channel) |

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 82 |
| P1 Tasks | 34 |
| P2 Tasks | 29 |
| P3 Tasks | 10 |
| Polish Tasks | 9 |
| Parallel Opportunities | 25 |
| User Stories | 11 |

---

## Notes

- `[P]` = Can run in parallel (different files, no blocking dependencies)
- `[USn]` = Maps to User Story n from spec.md
- US4 Rate limiting (Phase 2) is **foundational** - blocks all feature work
- Each user story is independently testable after completion
- GStreamer plugins required: `scaletempo`, `equalizer-10bands`
- Redis required for rate limiting and priority queues
- Genius API key required for lyrics (FR-012)
- Shazam has 10 req/min limit (Technical Decision TD-006)
