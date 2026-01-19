"""
StopBroadcastUseCase - Use Case остановки трансляции

Ответственность:
- Загрузка Stream entity
- Проверка прав владельца (authorization)
- Переход Stream в состояние STOPPED
- Остановка video stream в Telegram
- Отключение от Telegram
- Публикация StreamStoppedEvent

Зависимости (через порты):
- IStreamRepository: Загрузка и сохранение Stream
- ITelegramClient: Остановка video stream и отключение
- IEventBus: Публикация domain events
"""

from datetime import datetime
from typing import Optional

from src.application.dtos.broadcast import (
    StopBroadcastRequest,
    StopBroadcastResponse,
)
from src.application.errors import BroadcastError
from src.application.ports.i_event_bus import IEventBus
from src.application.ports.i_stream_repository import IStreamRepository
from src.application.ports.i_telegram_client import ITelegramClient
from src.domain.value_objects.stream_id import StreamId
from src.domain.value_objects.user_id import UserId
from src.shared.kernel.result import Result


class StopBroadcastUseCase:
    """
    Use Case: Остановка трансляции стрима в Telegram чате.
    
    Orchestration:
    1. Валидировать stream_id и user_id
    2. Загрузить Stream entity из репозитория
    3. Проверить права владельца (stream.owner_id == user_id)
    4. Вызвать stream.stop() для изменения состояния (бизнес-правило)
    5. Остановить video stream в Telegram (stop_video_stream)
    6. Отключиться от Telegram
    7. Сохранить изменения через репозиторий
    8. Опубликовать StreamStoppedEvent
    9. Вернуть StopBroadcastResponse
    
    Пример использования:
        use_case = StopBroadcastUseCase(stream_repo, telegram_client, event_bus)
        request = StopBroadcastRequest(
            stream_id=1,
            user_id=1
        )
        result = use_case.execute(request)
        
        match result:
            case Ok(response):
                print(f"Broadcast stopped: {response.stream_id} at {response.stopped_at}")
            case Err(error):
                print(f"Stop failed: {error.message}")
    """
    
    def __init__(
        self,
        stream_repository: IStreamRepository,
        telegram_client: ITelegramClient,
        event_bus: IEventBus,
    ):
        """
        Инициализация Use Case с зависимостями (Dependency Injection).
        
        Args:
            stream_repository: Репозиторий для работы со стримами
            telegram_client: Клиент Telegram для управления video stream
            event_bus: Шина событий для публикации domain events
        """
        self._stream_repository = stream_repository
        self._telegram_client = telegram_client
        self._event_bus = event_bus
    
    def execute(
        self,
        request: StopBroadcastRequest
    ) -> Result[StopBroadcastResponse, BroadcastError]:
        """
        Выполнить остановку трансляции.
        
        Args:
            request: DTO с stream_id, user_id
        
        Returns:
            Result[StopBroadcastResponse, BroadcastError]:
                Ok: Response с stream_id, status=STOPPED, stopped_at
                Err: BroadcastError (stream_not_found, permission_denied, invalid_state_transition)
        """
        # 1. Валидировать stream_id
        stream_id_result = StreamId.create(request.stream_id)
        if stream_id_result.is_failure:
            return Result.failure(
                BroadcastError.stream_not_found(request.stream_id)
            )
        
        stream_id = stream_id_result.value
        
        # 2. Валидировать user_id
        user_id_result = UserId.create(request.user_id)
        if user_id_result.is_failure:
            return Result.failure(
                BroadcastError.permission_denied(request.user_id, request.stream_id)
            )
        
        user_id = user_id_result.value
        
        # 3. Загрузить Stream из репозитория
        stream = self._stream_repository.get_by_id(stream_id)
        if stream is None:
            return Result.failure(
                BroadcastError.stream_not_found(request.stream_id)
            )
        
        # 4. Проверить права владельца (authorization)
        if stream.owner_id != user_id:
            return Result.failure(
                BroadcastError.permission_denied(request.user_id, request.stream_id)
            )
        
        # 5. Вызвать stream.stop() (бизнес-правило: проверка состояния)
        stop_result = stream.stop()
        if stop_result.is_failure:
            error = stop_result.unwrap_err()
            return Result.failure(
                BroadcastError.invalid_state_transition(
                    current_state=stream.status.value,
                    target_action="stop"
                )
            )
        
        # 6. Остановить video stream в Telegram
        try:
            self._telegram_client.stop_video_stream(chat_id=stream.chat_id)
        except Exception as e:
            # Логирование ошибки, но не блокируем остановку
            # В production: retry логика или компенсация
            print(f"Warning: Failed to stop Telegram stream: {e}")
        
        # 7. Отключиться от Telegram (опционально, если нет других активных стримов)
        try:
            self._telegram_client.disconnect()
        except Exception as e:
            # Не критично, если отключение не удалось
            print(f"Warning: Failed to disconnect from Telegram: {e}")
        
        # 8. Сохранить изменения (status = STOPPED)
        self._stream_repository.save(stream)
        
        # 9. Публикация domain event
        # TODO: StreamStoppedEvent для интеграции (статистика, уведомления)
        # self._event_bus.publish(
        #     StreamStoppedEvent(
        #         stream_id=stream.id,
        #         chat_id=stream.chat_id,
        #         stopped_at=datetime.utcnow(),
        #         duration=datetime.utcnow() - stream.started_at  # Длительность трансляции
        #     )
        # )
        
        # 10. Сформировать Response DTO
        response = StopBroadcastResponse(
            stream_id=stream.id.value,
            status=stream.status.value,  # StreamStatus.STOPPED
            stopped_at=datetime.utcnow(),
        )
        
        return Result.ok(response)
