"""
ITelegramClient Port Interface

Контракт для взаимодействия с Telegram API.
"""

from typing import Protocol, Optional
from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.file_path import FilePath


class ITelegramClient(Protocol):
    """
    Интерфейс клиента Telegram API.
    
    Изолирует Application layer от конкретной библиотеки (Pyrogram, Telethon, aiogram).
    Позволяет легко менять реализацию или создавать моки для тестов.
    
    Examples:
        >>> await client.connect()
        >>> await client.start_video_stream(chat_id, file_path)
        >>> await client.stop_video_stream(chat_id)
        >>> await client.disconnect()
    """
    
    async def connect(self) -> None:
        """
        Установить соединение с Telegram.
        
        Raises:
            TelegramConnectionError: При ошибке подключения
        """
        ...
    
    async def disconnect(self) -> None:
        """
        Закрыть соединение с Telegram.
        
        Raises:
            TelegramConnectionError: При ошибке отключения
        """
        ...
    
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
        ...
    
    async def stop_video_stream(self, chat_id: ChatId) -> None:
        """
        Остановить видео трансляцию в чате.
        
        Args:
            chat_id: ID чата с активной трансляцией
            
        Raises:
            TelegramStreamError: При ошибке остановки трансляции
            NoActiveStreamError: Если нет активной трансляции
        """
        ...
    
    async def pause_video_stream(self, chat_id: ChatId) -> None:
        """
        Приостановить видео трансляцию в чате.
        
        Args:
            chat_id: ID чата с активной трансляцией
            
        Raises:
            TelegramStreamError: При ошибке паузы трансляции
            NoActiveStreamError: Если нет активной трансляции
        """
        ...
    
    async def resume_video_stream(self, chat_id: ChatId) -> None:
        """
        Возобновить видео трансляцию в чате.
        
        Args:
            chat_id: ID чата с приостановленной трансляцией
            
        Raises:
            TelegramStreamError: При ошибке возобновления трансляции
            NoActiveStreamError: Если нет приостановленной трансляции
        """
        ...
    
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
        ...
