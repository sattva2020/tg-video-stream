# Tasks: Stream Quality Monitoring (Spec 022)

**Prerequisites**: Spec 021 (Analytics) infrastructure is useful (Recharts, etc.).

## Phase 1: Backend Infrastructure (Completed)
- [X] T001 Create `StreamMetric` and `StreamIncident` models in `backend/src/models/stream_quality.py`
- [X] T002 Generate Alembic migration for monitoring tables (`22_phase3_stream_quality_history.py`)
- [X] T003 Implement `StreamQualityService` in `backend/src/services/stream_quality_service.py`
- [X] T004 Implement `QualityTrendsService` in `backend/src/services/quality_trends_service.py`
- [X] T005 Create Pydantic schemas in `backend/src/schemas/stream_quality.py`

## Phase 2: API Implementation (Completed)
- [X] T006 Create `backend/src/api/routes/stream_quality.py`
  - `GET /api/admin/stream-quality/current` - Get current stream status (using `StreamQualityService`)
  - `GET /api/admin/stream-quality/history` - Get historical data (using `QualityTrendsService`)
  - `GET /api/admin/stream-quality/alerts` - Get alert configuration
  - `PUT /api/admin/stream-quality/alerts` - Update alert configuration
- [X] T007 Register router in `backend/src/api/admin.py` or `backend/src/main.py`
- [X] T008 Add RBAC (Admin only) to endpoints.

## Phase 3: Frontend Visualization (Completed)
- [X] T009 Create `StreamHealthWidget.tsx` in `frontend/src/components/admin/stream-quality/`
  - Display "Online/Offline", "Bitrate", "Quality Score".
- [X] T010 Create `StreamQualityHistoryChart.tsx` using Recharts
  - Line chart of bitrate/quality over time.
- [X] T011 Create `StreamQualityPage.tsx` in `frontend/src/pages/admin/`
  - Combine Widget, Chart, and Alert Config.
- [X] T012 Add "Stream Quality" item to Admin Navigation (under Analytics or separate).

## Phase 4: Alerting & Polish (Completed)
- [X] T013 Implement alerting logic in `QualityTrendsService` (verified existing implementation).
- [X] T014 Add i18n translations for new widgets (RU/EN).
- [X] T015 Write documentation in `docs/features/stream-quality.md`.

## Summary
All tasks for Spec 022 are complete.
- Backend: Models, Services, API Routes implemented.
- Frontend: Widgets, Charts, Page, Navigation implemented.
- Docs: Feature documentation created.
- i18n: Translations added.
