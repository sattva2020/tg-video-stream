"""
Activity Service
Spec: 015-real-system-monitoring

Сервис для логирования и получения событий активности.
Используется для отображения в блоке "Активность" на Dashboard.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from src.models.activity_event import ActivityEvent
from src.api.schemas.system import (
    ActivityEventResponse,
    ActivityEventsListResponse,
    ActivityEventCreate,
)


logger = logging.getLogger(__name__)

# Лимит хранения событий
MAX_EVENTS = 1000
CLEANUP_THRESHOLD = 100  # Гистерезис для cleanup


class ActivityService:
    """
    Сервис для работы с событиями активности.
    
    Обеспечивает:
    - Логирование новых событий
    - Получение списка событий с фильтрацией и пагинацией
    - Автоматическую очистку старых записей
    """

    def __init__(self, db: Session):
        """
        Инициализация сервиса.
        
        Args:
            db: SQLAlchemy сессия
        """
        self.db = db

    def log_event(
        self,
        event_type: str,
        message: str,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ) -> ActivityEvent:
        """
        Логирует новое событие активности.
        
        Args:
            event_type: Тип события (user_login, stream_start, etc.)
            message: Текст сообщения
            user_id: ID пользователя (опционально, для логирования)
            user_email: Email пользователя (опционально)
            details: Дополнительные данные (опционально)
        
        Returns:
            Созданная запись ActivityEvent
        """
        # user_id передаётся для совместимости, но не сохраняется в БД
        # (модель хранит только user_email)
        event = ActivityEvent(
            type=event_type,
            message=message,
            user_email=user_email,
            details=details,
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        # Очистка старых событий после добавления
        self._cleanup_old_events()
        
        logger.info(f"Activity logged: {event_type} - {message}")
        return event

    def get_events(
        self,
        limit: int = 20,
        offset: int = 0,
        event_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> ActivityEventsListResponse:
        """
        Получает список событий с пагинацией и фильтрацией.
        
        Args:
            limit: Максимальное количество записей (1-100)
            offset: Смещение для пагинации
            event_type: Фильтр по типу события (опционально)
            search: Поиск по тексту сообщения (опционально)
        
        Returns:
            ActivityEventsListResponse со списком событий и общим количеством
        """
        # Валидация параметров
        limit = max(1, min(100, limit))
        offset = max(0, offset)

        query = self.db.query(ActivityEvent)

        # Фильтр по типу
        if event_type:
            query = query.filter(ActivityEvent.type == event_type)

        # Поиск по сообщению
        if search:
            query = query.filter(ActivityEvent.message.ilike(f"%{search}%"))

        # Общее количество
        total = query.count()

        # Сортировка и пагинация
        events = (
            query
            .order_by(desc(ActivityEvent.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        # Преобразование в Pydantic модели
        event_responses = [
            ActivityEventResponse(
                id=event.id,
                type=event.type,
                message=event.message,
                user_email=event.user_email,
                details=event.details,
                created_at=event.created_at
            )
            for event in events
        ]

        return ActivityEventsListResponse(
            events=event_responses,
            total=total
        )

    def _cleanup_old_events(self) -> None:
        """
        Удаляет старые события, оставляя последние MAX_EVENTS записей.
        
        Использует гистерезис для уменьшения частоты операций:
        очистка происходит только когда count > MAX_EVENTS + CLEANUP_THRESHOLD
        """
        try:
            count = self.db.query(func.count(ActivityEvent.id)).scalar() or 0
            
            if count <= MAX_EVENTS + CLEANUP_THRESHOLD:
                return

            # Находим ID для сохранения
            keep_ids_subquery = (
                self.db.query(ActivityEvent.id)
                .order_by(desc(ActivityEvent.created_at))
                .limit(MAX_EVENTS)
                .subquery()
            )

            # Удаляем все, что не в списке сохранения
            deleted = (
                self.db.query(ActivityEvent)
                .filter(~ActivityEvent.id.in_(keep_ids_subquery.select()))
                .delete(synchronize_session='fetch')
            )
            
            self.db.commit()
            logger.info(f"Cleaned up {deleted} old activity events")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            self.db.rollback()
            return 0

    def cleanup_old_events(self, max_events: int = MAX_EVENTS) -> int:
        """
        Публичный метод очистки старых событий.
        
        Args:
            max_events: Максимальное количество событий для сохранения
        
        Returns:
            Количество удалённых записей
        """
        try:
            count = self.db.query(func.count(ActivityEvent.id)).scalar() or 0
            
            if count <= max_events:
                return 0

            # Находим ID для сохранения
            keep_ids_subquery = (
                self.db.query(ActivityEvent.id)
                .order_by(desc(ActivityEvent.created_at))
                .limit(max_events)
                .subquery()
            )

            # Удаляем все, что не в списке сохранения
            deleted = (
                self.db.query(ActivityEvent)
                .filter(~ActivityEvent.id.in_(keep_ids_subquery.select()))
                .delete(synchronize_session='fetch')
            )
            
            self.db.commit()
            logger.info(f"Cleaned up {deleted} old activity events (max_events={max_events})")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            self.db.rollback()
            return 0

    def delete_all_events(self) -> int:
        """
        Удаляет все события (для тестирования/администрирования).
        
        Returns:
            Количество удалённых записей
        """
        try:
            deleted = self.db.query(ActivityEvent).delete()
            self.db.commit()
            logger.info(f"Deleted all {deleted} activity events")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete all events: {e}")
            self.db.rollback()
            return 0


def get_activity_service(db: Session) -> ActivityService:
    """
    Фабричная функция для создания ActivityService.
    
    Args:
        db: SQLAlchemy сессия
    
    Returns:
        Экземпляр ActivityService
    """
    return ActivityService(db=db)


# === Хелперы для логирования событий ===

def log_user_login(db: Session, email: str, ip: Optional[str] = None) -> None:
    """Логирует вход пользователя."""
    service = get_activity_service(db)
    details = {"ip": ip} if ip else None
    service.log_event("user_login", "Пользователь вошёл в систему", email, details)


def log_user_logout(db: Session, email: str) -> None:
    """Логирует выход пользователя."""
    service = get_activity_service(db)
    service.log_event("user_logout", "Пользователь вышел из системы", email)


def log_stream_start(db: Session, user_email: Optional[str] = None) -> None:
    """Логирует запуск стрима."""
    service = get_activity_service(db)
    service.log_event("stream_start", "Стрим запущен", user_email)


def log_stream_stop(db: Session, user_email: Optional[str] = None, reason: Optional[str] = None) -> None:
    """Логирует остановку стрима."""
    service = get_activity_service(db)
    details = {"reason": reason} if reason else None
    service.log_event("stream_stop", "Стрим остановлен", user_email, details)


def log_stream_error(db: Session, error: str, user_email: Optional[str] = None) -> None:
    """Логирует ошибку стрима."""
    service = get_activity_service(db)
    service.log_event("stream_error", f"Ошибка стрима: {error}", user_email, {"error": error})


def log_track_added(db: Session, track_url: str, user_email: Optional[str] = None) -> None:
    """Логирует добавление трека."""
    service = get_activity_service(db)
    service.log_event("track_added", "Трек добавлен в плейлист", user_email, {"url": track_url})


def log_track_removed(db: Session, track_url: str, user_email: Optional[str] = None) -> None:
    """Логирует удаление трека."""
    service = get_activity_service(db)
    service.log_event("track_removed", "Трек удалён из плейлиста", user_email, {"url": track_url})


def log_playlist_updated(db: Session, user_email: Optional[str] = None) -> None:
    """Логирует обновление плейлиста."""
    service = get_activity_service(db)
    service.log_event("playlist_updated", "Плейлист обновлён", user_email)


def log_system_warning(db: Session, message: str, details: Optional[dict] = None) -> None:
    """Логирует системное предупреждение."""
    service = get_activity_service(db)
    service.log_event("system_warning", message, None, details)


def log_system_error(db: Session, message: str, details: Optional[dict] = None) -> None:
    """Логирует системную ошибку."""
    service = get_activity_service(db)
    service.log_event("system_error", message, None, details)
