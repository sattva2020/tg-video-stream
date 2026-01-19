"""
Pyrogram реализация Telegram клиента.

Этот модуль реализует ITelegramClient port используя Pyrogram библиотеку.
"""

from typing import Optional
from pyrogram import Client
from pyrogram.errors import RPCError

from src.application.ports.i_telegram_client import ITelegramClient
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.file_path import FilePath
from src.domain.errors import (
    TelegramConnectionError,
    TelegramStreamError,
    TelegramAPIError,
    ChatNotFoundError,
    NoActiveStreamError
)


class PyrogramTelegramClient:
    """
    Pyrogram реализация ITelegramClient.
    
    Использует Pyrogram для взаимодействия с Telegram API и MTProto.
    """
    
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_name: str = "streamer_bot"
    ):
        """
        Инициализация клиента.
        
        Args:
            api_id: Telegram API ID (из my.telegram.org)
            api_hash: Telegram API Hash
            session_name: Имя сессии для хранения авторизации
        """
        self._client = Client(
            name=session_name,
            api_id=api_id,
            api_hash=api_hash
        )
        self._active_streams: dict[int, bool] = {}  # {chat_id: is_active}
    
    async def connect(self) -> None:
        """
        Установить соединение с Telegram.
        
        Raises:
            TelegramConnectionError: При ошибке подключения
        """
        try:
            await self._client.start()
        except RPCError as e:
            raise TelegramConnectionError(f"Failed to connect to Telegram: {e}") from e
        except Exception as e:
            raise TelegramConnectionError(f"Unexpected connection error: {e}") from e
    
    async def disconnect(self) -> None:
        """
        Закрыть соединение с Telegram.
        
        Raises:
            TelegramConnectionError: При ошибке отключения
        """
        try:
            await self._client.stop()
        except Exception as e:
            raise TelegramConnectionError(f"Failed to disconnect: {e}") from e
    
    async def start_video_stream(
        self, 
        chat_id: ChatId, 
        file_path: FilePath
    ) -> None:
        """
        Начать видео трансляцию в чат.
        
        Args:
            chat_id: ID чата для трансляции
            file_path: Путь к видео файлу
            
        Raises:
            TelegramStreamError: При ошибке запуска трансляции
            ChatNotFoundError: Если чат не найден
            FileNotFoundError: Если файл не найден
        """
        try:
            # TODO: Implement video stream using pytgcalls or similar
            # Placeholder implementation
            chat_id_int = chat_id.value
            
            # Проверяем существование чата
            try:
                await self._client.get_chat(chat_id_int)
            except RPCError as e:
                if "CHAT_ID_INVALID" in str(e):
                    raise ChatNotFoundError(f"Chat {chat_id} not found") from e
                raise
            
            # Проверяем файл
            if not file_path.exists():
                raise FileNotFoundError(f"File {file_path} not found")
            
            # TODO: Start actual video stream
            self._active_streams[chat_id_int] = True
            
        except (ChatNotFoundError, FileNotFoundError):
            raise  # Re-raise domain errors
        except RPCError as e:
            raise TelegramStreamError(f"Failed to start stream: {e}") from e
        except Exception as e:
            raise TelegramStreamError(f"Unexpected stream error: {e}") from e
    
    async def stop_video_stream(self, chat_id: ChatId) -> None:
        """
        Остановить видео трансляцию в чате.
        
        Args:
            chat_id: ID чата с активной трансляцией
            
        Raises:
            TelegramStreamError: При ошибке остановки трансляции
            NoActiveStreamError: Если нет активной трансляции
        """
        try:
            chat_id_int = chat_id.value
            
            if chat_id_int not in self._active_streams:
                raise NoActiveStreamError(f"No active stream in chat {chat_id}")
            
            # TODO: Stop actual video stream
            del self._active_streams[chat_id_int]
            
        except NoActiveStreamError:
            raise  # Re-raise domain errors
        except Exception as e:
            raise TelegramStreamError(f"Failed to stop stream: {e}") from e
    
    async def pause_video_stream(self, chat_id: ChatId) -> None:
        """
        Приостановить видео трансляцию в чате.
        
        Args:
            chat_id: ID чата с активной трансляцией
            
        Raises:
            TelegramStreamError: При ошибке паузы трансляции
            NoActiveStreamError: Если нет активной трансляции
        """
        try:
            chat_id_int = chat_id.value
            
            if chat_id_int not in self._active_streams:
                raise NoActiveStreamError(f"No active stream in chat {chat_id}")
            
            # TODO: Pause actual video stream
            # Placeholder: mark as paused
            self._active_streams[chat_id_int] = False
            
        except NoActiveStreamError:
            raise  # Re-raise domain errors
        except Exception as e:
            raise TelegramStreamError(f"Failed to pause stream: {e}") from e
    
    async def resume_video_stream(self, chat_id: ChatId) -> None:
        """
        Возобновить видео трансляцию в чате.
        
        Args:
            chat_id: ID чата с приостановленной трансляцией
            
        Raises:
            TelegramStreamError: При ошибке возобновления трансляции
            NoActiveStreamError: Если нет приостановленной трансляции
        """
        try:
            chat_id_int = chat_id.value
            
            if chat_id_int not in self._active_streams:
                raise NoActiveStreamError(f"No paused stream in chat {chat_id}")
            
            # TODO: Resume actual video stream
            self._active_streams[chat_id_int] = True
            
        except NoActiveStreamError:
            raise  # Re-raise domain errors
        except Exception as e:
            raise TelegramStreamError(f"Failed to resume stream: {e}") from e
    
    async def get_chat_title(self, chat_id: ChatId) -> Optional[str]:
        """
        Получить название чата.
        
        Args:
            chat_id: ID чата
            
        Returns:
            Название чата или None если чат не найден
            
        Raises:
            TelegramAPIError: При ошибке запроса к API
        """
        try:
            chat = await self._client.get_chat(chat_id.value)
            return chat.title if hasattr(chat, 'title') else None
            
        except RPCError as e:
            if "CHAT_ID_INVALID" in str(e):
                return None  # Chat not found
            raise TelegramAPIError(f"Failed to get chat title: {e}") from e
        except Exception as e:
            raise TelegramAPIError(f"Unexpected API error: {e}") from e
