"""
Streaming & Broadcast Errors

Ошибки Use Cases для управления стримами и трансляциями.
"""

from src.domain.errors import DomainError


class StreamCreationError(DomainError):
    """Ошибка создания стрима."""
    
    def __init__(self, message: str, code: str = "stream_creation_error"):
        super().__init__(message)
        self.code = code
    
    @staticmethod
    def user_not_found(user_id: int) -> "StreamCreationError":
        """Пользователь не найден."""
        return StreamCreationError(f"User with id {user_id} not found", code="user_not_found")
    
    @staticmethod
    def invalid_chat_id(chat_id: str | int) -> "StreamCreationError":
        """Невалидный chat_id."""
        return StreamCreationError(f"Chat ID {chat_id} is invalid", code="invalid_chat_id")
    
    @staticmethod
    def chat_not_accessible(chat_id: str | int) -> "StreamCreationError":
        """Чат недоступен."""
        return StreamCreationError(f"Chat {chat_id} is not accessible", code="chat_not_accessible")
    
    @staticmethod
    def no_tracks_provided() -> "StreamCreationError":
        """Не указаны треки."""
        return StreamCreationError("At least one track must be provided", code="no_tracks_provided")


class BroadcastError(DomainError):
    """Ошибка управления трансляцией."""
    
    def __init__(self, message: str, code: str = "broadcast_error"):
        super().__init__(message)
        self.code = code
    
    @staticmethod
    def stream_not_found(stream_id: int) -> "BroadcastError":
        """Стрим не найден."""
        return BroadcastError(f"Stream with id {stream_id} not found", code="stream_not_found")
    
    @staticmethod
    def permission_denied(user_id: int, stream_id: int) -> "BroadcastError":
        """Нет прав на управление стримом."""
        return BroadcastError(
            f"User {user_id} does not have permission to manage stream {stream_id}",
            code="permission_denied"
        )
    
    @staticmethod
    def invalid_state_transition(current_state: str, target_action: str) -> "BroadcastError":
        """Невалидный переход состояния."""
        return BroadcastError(
            f"Cannot {target_action} stream in {current_state} state",
            code="invalid_state_transition"
        )
    
    @staticmethod
    def telegram_connection_failed(reason: str) -> "BroadcastError":
        """Ошибка подключения к Telegram."""
        return BroadcastError(f"Failed to connect to Telegram: {reason}", code="telegram_connection_failed")
    
    @staticmethod
    def stream_start_failed(reason: str) -> "BroadcastError":
        """Ошибка запуска стрима."""
        return BroadcastError(f"Failed to start stream: {reason}", code="stream_start_failed")
