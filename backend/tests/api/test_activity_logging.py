"""
Tests для ActivityService — логирования системных событий.
Spec: 015-real-system-monitoring
"""

import pytest
from datetime import datetime, timedelta

from src.services.activity_service import ActivityService


class TestActivityLogging:
    """Тесты записи событий через ActivityService."""

    @pytest.fixture
    def activity_service(self, db_session):
        """Фикстура ActivityService с тестовой сессией."""
        return ActivityService(db_session)

    def test_log_event_creates_record(self, activity_service, db_session):
        """log_event создаёт запись в БД."""
        event = activity_service.log_event(
            event_type="user_registered",
            message="Тестовый пользователь зарегистрировался",
            user_id=1,
            user_email="test@example.com"
        )

        assert event is not None
        assert event.id is not None
        assert event.type == "user_registered"
        assert event.message == "Тестовый пользователь зарегистрировался"
        assert event.user_id == 1
        assert event.user_email == "test@example.com"

    def test_log_event_with_details(self, activity_service):
        """log_event сохраняет JSON details."""
        details = {"track_title": "Test Track", "duration": 180}
        
        event = activity_service.log_event(
            event_type="track_added",
            message="Добавлен новый трек",
            details=details
        )

        assert event.details == details

    def test_log_event_without_user(self, activity_service):
        """log_event работает без user_id и user_email."""
        event = activity_service.log_event(
            event_type="stream_started",
            message="Трансляция запущена"
        )

        assert event is not None
        assert event.user_id is None
        assert event.user_email is None

    def test_log_event_created_at_is_now(self, activity_service):
        """created_at устанавливается близко к текущему времени."""
        before = datetime.utcnow()
        event = activity_service.log_event(
            event_type="test",
            message="Тестовое событие"
        )
        after = datetime.utcnow()

        assert before <= event.created_at <= after


class TestActivityEventTypes:
    """Тесты различных типов событий."""

    @pytest.fixture
    def activity_service(self, db_session):
        return ActivityService(db_session)

    @pytest.mark.parametrize("event_type", [
        "user_registered",
        "user_approved",
        "user_rejected",
        "stream_started",
        "stream_stopped",
        "track_added",
        "track_removed",
        "system_error",
        "system_warning",
    ])
    def test_supported_event_types(self, activity_service, event_type):
        """Все поддерживаемые типы событий записываются."""
        event = activity_service.log_event(
            event_type=event_type,
            message=f"Событие типа {event_type}"
        )

        assert event is not None
        assert event.type == event_type


class TestActivityCleanup:
    """Тесты очистки старых событий."""

    @pytest.fixture
    def activity_service(self, db_session):
        return ActivityService(db_session)

    def test_cleanup_removes_old_events(self, activity_service, db_session):
        """cleanup удаляет события старше лимита."""
        from src.models.activity_event import ActivityEvent

        # Создаём >1000 событий
        for i in range(1010):
            activity_service.log_event(
                event_type="test",
                message=f"Событие {i}"
            )

        # Подтверждаем создание
        db_session.commit()

        # Проверяем, что создано больше 1000
        count_before = db_session.query(ActivityEvent).count()
        assert count_before >= 1010

        # Запускаем cleanup
        deleted_count = activity_service.cleanup_old_events(max_events=1000)

        # Должно остаться ровно 1000
        count_after = db_session.query(ActivityEvent).count()
        assert count_after == 1000
        assert deleted_count >= 10


class TestActivityQueries:
    """Тесты запросов событий."""

    @pytest.fixture
    def activity_service(self, db_session):
        service = ActivityService(db_session)
        
        # Создаём тестовые события
        service.log_event("user_registered", "User 1 registered", user_email="user1@test.com")
        service.log_event("user_registered", "User 2 registered", user_email="user2@test.com")
        service.log_event("stream_started", "Stream started")
        service.log_event("track_added", "Track added", details={"title": "Song A"})
        service.log_event("track_added", "Track added", details={"title": "Song B"})
        
        db_session.commit()
        return service

    def test_get_events_returns_list(self, activity_service):
        """get_events возвращает список событий."""
        events, total = activity_service.get_events(limit=10, offset=0)
        
        assert isinstance(events, list)
        assert total >= 5  # Минимум 5 созданных событий

    def test_get_events_respects_limit(self, activity_service):
        """get_events ограничивает количество результатов."""
        events, total = activity_service.get_events(limit=2, offset=0)
        
        assert len(events) <= 2
        assert total >= 5

    def test_get_events_respects_offset(self, activity_service):
        """get_events пропускает события согласно offset."""
        events1, _ = activity_service.get_events(limit=10, offset=0)
        events2, _ = activity_service.get_events(limit=10, offset=1)
        
        if len(events1) >= 2 and len(events2) >= 1:
            assert events2[0].id == events1[1].id

    def test_get_events_filter_by_type(self, activity_service):
        """get_events фильтрует по типу события."""
        events, total = activity_service.get_events(
            limit=10, 
            offset=0, 
            event_type="user_registered"
        )
        
        for event in events:
            assert event.type == "user_registered"

    def test_get_events_search(self, activity_service):
        """get_events ищет по тексту сообщения."""
        events, total = activity_service.get_events(
            limit=10,
            offset=0,
            search="User 1"
        )
        
        # Должно найти как минимум одно событие
        assert any("User 1" in e.message for e in events)
