# Plan: Stream Quality Monitoring (Spec 022)

## Phase 1: Backend Infrastructure
- [ ] Define SQLAlchemy models (`StreamMetric`, `StreamIncident`).
- [ ] Create Alembic migration.
- [ ] Implement `StreamMonitorService` to fetch stream stats.
- [ ] Create background task (APScheduler) to poll stream every 30s.

## Phase 2: API Implementation
- [ ] `GET /api/monitoring/stream/status`
- [ ] `GET /api/monitoring/stream/history`
- [ ] `GET /api/monitoring/incidents`
- [ ] Add RBAC (Admin only).

## Phase 3: Frontend Visualization
- [ ] Create `StreamHealthWidget` for Admin Dashboard.
- [ ] Create `StreamHistoryChart` (using Recharts).
- [ ] Create `IncidentLogTable`.
- [ ] Integrate into `AdminAnalytics` or separate `Monitoring` page.

## Phase 4: Alerting & Polish
- [ ] Implement alerting logic (if offline > 1 min -> notify).
- [ ] Add configuration (polling interval, thresholds) to Admin Settings.
- [ ] Write documentation.
