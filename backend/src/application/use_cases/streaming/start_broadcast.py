"""
StartBroadcastUseCase - Use Case запуска трансляции

Ответственность:
- Загрузка Stream entity
- Проверка прав владельца (authorization)
- Переход Stream в состояние ACTIVE
- Подключение к Telegram через ITelegramClient
- Запуск video stream в чате
- Публикация StreamStartedEvent

Зависимости (через порты):
- IStreamRepository: Загрузка и сохранение Stream
- ITelegramClient: Подключение и запуск video stream
- IEventBus: Публикация domain events
"""

from datetime import datetime
from typing import Optional

from src.application.dtos.broadcast import (
    StartBroadcastRequest,
    StartBroadcastResponse,
)
from src.application.errors import BroadcastError
from src.application.ports.i_event_bus import IEventBus
from src.application.ports.i_stream_repository import IStreamRepository
from src.application.ports.i_telegram_client import ITelegramClient
from src.domain.value_objects.stream_id import StreamId
from src.domain.value_objects.user_id import UserId
from src.shared.kernel.result import Result


class StartBroadcastUseCase:
    """
    Use Case: Запуск трансляции стрима в Telegram чат.
    
    Orchestration:
    1. Валидировать stream_id и user_id
    2. Загрузить Stream entity из репозитория
    3. Проверить права владельца (stream.owner_id == user_id)
    4. Вызвать stream.start() для изменения состояния (бизнес-правило)
    5. Подключиться к Telegram через ITelegramClient
    6. Запустить video stream в чате (start_video_stream)
    7. Сохранить изменения через репозиторий
    8. Опубликовать StreamStartedEvent
    9. Вернуть StartBroadcastResponse
    
    Пример использования:
        use_case = StartBroadcastUseCase(stream_repo, telegram_client, event_bus)
        request = StartBroadcastRequest(
            stream_id=1,
            user_id=1
        )
        result = use_case.execute(request)
        
        match result:
            case Ok(response):
                print(f"Broadcast started: {response.stream_id} in chat {response.chat_id}")
            case Err(error):
                print(f"Start failed: {error.message}")
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
    
    async def execute(
        self,
        request: StartBroadcastRequest
    ) -> Result[StartBroadcastResponse, BroadcastError]:
        """
        Выполнить запуск трансляции.
        
        Args:
            request: DTO с stream_id, user_id
        
        Returns:
            Result[StartBroadcastResponse, BroadcastError]:
                Ok: Response с stream_id, status=ACTIVE, started_at, chat_id, current_track_index
                Err: BroadcastError (stream_not_found, permission_denied, invalid_state_transition, telegram_connection_failed)
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
        stream = await self._stream_repository.get_by_id(stream_id)
        if stream is None:
            return Result.failure(
                BroadcastError.stream_not_found(request.stream_id)
            )
        
        # 4. Проверить права владельца (authorization)
        if stream.owner_id != user_id:
            return Result.failure(
                BroadcastError.permission_denied(request.user_id, request.stream_id)
            )
        
        # 5. Вызвать stream.start() (бизнес-правило: проверка состояния)
        try:
            stream.start()  # Raises BusinessRuleViolationError if already active
        except Exception as e:
            return Result.failure(
                BroadcastError.invalid_state_transition(
                    current_state=stream.status.value,
                    target_action="start"
                )
            )
        
        # 6. Подключиться к Telegram (если еще не подключен)
        try:
            await self._telegram_client.connect()
        except Exception as e:
            return Result.failure(
                BroadcastError.telegram_connection_failed(str(e))
            )
        
        # 7. Получить первый трек из плейлиста
        if stream.playlist is None or len(stream.playlist.tracks) == 0:
            return Result.failure(
                BroadcastError.stream_start_failed("No tracks in playlist")
            )
        
        first_track = stream.playlist.tracks[0]
        
        # 8. Запустить video stream в Telegram чате
        try:
            await self._telegram_client.start_video_stream(
                chat_id=stream.chat_id,
                file_path=first_track.file_path
            )
        except Exception as e:
            # Откатить состояние stream (rollback)
            stream._status = stream._status  # TODO: Реализовать stream.rollback()
            return Result.failure(
                BroadcastError.stream_start_failed(str(e))
            )
        
        # 9. Сохранить изменения (status = ACTIVE)
        await self._stream_repository.save(stream)
        
        # 10. Публикация domain event
        # TODO: StreamStartedEvent для интеграции (логирование, мониторинг)
        # self._event_bus.publish(
        #     StreamStartedEvent(
        #         stream_id=stream.id,
        #         chat_id=stream.chat_id,
        #         started_at=datetime.utcnow()
        #     )
        # )
        
        # 11. Сформировать Response DTO
        response = StartBroadcastResponse(
            stream_id=str(stream.id.value),
            status=stream.status.value,  # StreamStatus.ACTIVE
            started_at=datetime.utcnow(),
            chat_id=stream.chat_id.value,
            current_track_index=0,  # Первый трек
        )
        
        return Result.success(response)
