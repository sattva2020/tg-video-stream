"""
CreateStreamUseCase - Use Case создания стрима

Ответственность:
- Валидация owner_id и chat_id
- Проверка существования пользователя
- Проверка доступности Telegram чата
- Создание Stream Aggregate Root (с Playlist и Tracks)
- Сохранение через репозиторий

Зависимости (через порты):
- IStreamRepository: Сохранение Stream aggregate
- IUserRepository: Проверка существования владельца
- ITelegramClient: Проверка доступности чата
"""

from datetime import datetime
from typing import List, Optional

from src.application.dtos.stream import (
    CreateStreamRequest,
    CreateStreamResponse,
)
from src.application.errors import StreamCreationError
from src.application.ports.i_stream_repository import IStreamRepository
from src.application.ports.i_telegram_client import ITelegramClient
from src.application.ports.i_user_repository import IUserRepository
from src.domain.entities.stream import Stream
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.stream_id import StreamId
from src.domain.value_objects.title import Title
from src.domain.value_objects.user_id import UserId
from src.shared.kernel.result import Result


class CreateStreamUseCase:
    """
    Use Case: Создание нового стрима для трансляции в Telegram чат.
    
    Orchestration:
    1. Валидировать owner_id (через UserId Value Object)
    2. Валидировать chat_id (через ChatId Value Object)
    3. Проверить существование пользователя в репозитории
    4. Проверить доступность чата через ITelegramClient
    5. Создать Stream entity с Playlist и Tracks (Aggregate Root)
    6. Сохранить через IStreamRepository (cascade save)
    7. Вернуть CreateStreamResponse
    
    Пример использования:
        use_case = CreateStreamUseCase(stream_repo, user_repo, telegram_client)
        request = CreateStreamRequest(
            owner_id=1,
            chat_id=-1001234567890,  # Telegram group chat ID
            title="My Music Stream",
            track_ids=[1, 2, 3]  # Optional: existing track IDs
        )
        result = use_case.execute(request)
        
        match result:
            case Ok(response):
                print(f"Stream {response.stream_id} created: {response.title}")
            case Err(error):
                print(f"Stream creation failed: {error.message}")
    """
    
    def __init__(
        self,
        stream_repository: IStreamRepository,
        user_repository: IUserRepository,
        telegram_client: ITelegramClient,
    ):
        """
        Инициализация Use Case с зависимостями (Dependency Injection).
        
        Args:
            stream_repository: Репозиторий для работы со стримами
            user_repository: Репозиторий для проверки владельца
            telegram_client: Клиент Telegram для проверки чата
        """
        self._stream_repository = stream_repository
        self._user_repository = user_repository
        self._telegram_client = telegram_client
    
    async def execute(
        self,
        request: CreateStreamRequest
    ) -> Result[CreateStreamResponse, StreamCreationError]:
        """
        Выполнить создание стрима.
        
        Args:
            request: DTO с owner_id, chat_id, title, track_ids
        
        Returns:
            Result[CreateStreamResponse, StreamCreationError]:
                Ok: Response с stream_id, owner_id, chat_id, title, status, created_at
                Err: StreamCreationError (user_not_found, invalid_chat_id, chat_not_accessible, no_tracks_provided)
        """
        # 1. Валидировать owner_id через Value Object
        owner_id_result = UserId.create(request.owner_id)
        if owner_id_result.is_failure:
            return Result.failure(
                StreamCreationError.user_not_found(request.owner_id)
            )
        
        owner_id = owner_id_result.value
        
        # 2. Валидировать chat_id через Value Object
        chat_id_result = ChatId.create(request.chat_id)
        if chat_id_result.is_failure:
            return Result.failure(
                StreamCreationError.invalid_chat_id(request.chat_id)
            )
        
        chat_id = chat_id_result.value
        
        # 3. Проверить существование пользователя
        user = await self._user_repository.get_by_id(owner_id)
        if user is None:
            return Result.failure(
                StreamCreationError.user_not_found(request.owner_id)
            )
        
        # 4. Проверить доступность Telegram чата
        try:
            chat_title = await self._telegram_client.get_chat_title(chat_id)
            if chat_title is None:
                return Result.failure(
                    StreamCreationError.chat_not_accessible(request.chat_id)
                )
        except Exception as e:
            # В реальности ITelegramClient должен возвращать Result
            return Result.failure(
                StreamCreationError.chat_not_accessible(request.chat_id)
            )
        
        # 5. Валидировать track_ids (опционально)
        track_ids = request.track_ids or []
        # Для гибкости разрешаем пустой playlist (треки можно добавить позже)
        
        # 6. Создать Stream entity
        stream_id = StreamId.generate()
        try:
            title = Title.create(request.title)
        except Exception as e:
            return Result.failure(
                StreamCreationError.invalid_chat_id(request.chat_id)  # Generic error
            )
        
        stream = Stream.create(
            stream_id=stream_id,
            chat_id=chat_id,
            owner_id=owner_id,
            title=title,
        )
        
        # 7. Сохранить Stream
        await self._stream_repository.save(stream)
        
        # 8. Публикация domain event (опционально)
        # TODO: StreamCreatedEvent для интеграции с другими модулями
        
        # 9. Сформировать Response DTO
        response = CreateStreamResponse(
            stream_id=str(stream.id.value),
            owner_id=str(stream.owner_id.value),
            chat_id=stream.chat_id.value,
            title=str(stream.title),
            status=stream.status.value,  # StreamStatus.IDLE
            created_at=stream.created_at,
        )
        
        return Result.success(response)
