"""
Placeholder Audio/Video Player

Модуль для воспроизведения заглушки (placeholder) при пустой очереди.

Placeholder воспроизводится в цикле до:
- Появления нового элемента в очереди
- Ручной остановки
- Срабатывания auto-end таймера

Использование:
    placeholder = PlaceholderPlayer(pytg, chat_id)
    await placeholder.start()  # Начать воспроизведение заглушки
    await placeholder.stop()   # Остановить
"""

import os
import asyncio
import logging
from typing import Optional, Union, Callable, Awaitable

log = logging.getLogger("tg_video_streamer.placeholder")

# Попытка импорта pytgcalls
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import AudioPiped, HighQualityAudio
    PYTG_AVAILABLE = True
except ImportError:
    PYTG_AVAILABLE = False
    log.warning("pytgcalls not available — PlaceholderPlayer disabled")


class PlaceholderPlayer:
    """
    Воспроизводитель заглушки для пустой очереди.
    
    Attributes:
        pytg: Экземпляр PyTgCalls
        chat_id: ID чата/канала
        placeholder_path: Путь к файлу заглушки
        is_playing: Флаг активного воспроизведения
    """
    
    # Настройки по умолчанию
    DEFAULT_PLACEHOLDER_PATH = "static/placeholder.mp3"
    
    def __init__(
        self,
        pytg: Optional["PyTgCalls"],
        chat_id: Union[int, str],
        placeholder_path: Optional[str] = None,
        on_stop_callback: Optional[Callable[[], Awaitable[None]]] = None
    ):
        """
        Инициализация PlaceholderPlayer.
        
        Args:
            pytg: Экземпляр PyTgCalls
            chat_id: ID чата для воспроизведения
            placeholder_path: Путь к аудио-файлу заглушки
            on_stop_callback: Callback при остановке placeholder
        """
        self.pytg = pytg
        self.chat_id = chat_id
        self.placeholder_path = placeholder_path or self._get_default_path()
        self.on_stop_callback = on_stop_callback
        
        self._is_playing = False
        self._play_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
    
    @staticmethod
    def _get_default_path() -> str:
        """Получить путь к placeholder из env или default."""
        return os.getenv("PLACEHOLDER_AUDIO_PATH", PlaceholderPlayer.DEFAULT_PLACEHOLDER_PATH)
    
    @property
    def is_playing(self) -> bool:
        """Воспроизводится ли сейчас placeholder."""
        return self._is_playing
    
    def _check_file_exists(self) -> bool:
        """Проверить существование файла placeholder."""
        if not os.path.exists(self.placeholder_path):
            log.warning(f"Placeholder file not found: {self.placeholder_path}")
            return False
        return True
    
    async def start(self) -> bool:
        """
        Начать воспроизведение placeholder.
        
        Returns:
            True если воспроизведение началось
        """
        if not PYTG_AVAILABLE or not self.pytg:
            log.warning("PyTgCalls not available, cannot start placeholder")
            return False
        
        if self._is_playing:
            log.debug("Placeholder already playing")
            return True
        
        if not self._check_file_exists():
            log.error(f"Cannot start placeholder: file not found at {self.placeholder_path}")
            return False
        
        self._stop_event.clear()
        self._is_playing = True
        self._play_task = asyncio.create_task(self._play_loop())
        
        log.info(f"Placeholder started: {self.placeholder_path}")
        return True
    
    async def stop(self) -> None:
        """Остановить воспроизведение placeholder."""
        if not self._is_playing:
            return
        
        self._stop_event.set()
        self._is_playing = False
        
        if self._play_task:
            self._play_task.cancel()
            try:
                await self._play_task
            except asyncio.CancelledError:
                pass
            self._play_task = None
        
        # Покинуть голосовой чат
        try:
            if self.pytg:
                await self.pytg.leave_group_call(self.chat_id)
        except Exception as e:
            log.debug(f"Error leaving group call: {e}")
        
        log.info("Placeholder stopped")
        
        # Вызов callback
        if self.on_stop_callback:
            try:
                await self.on_stop_callback()
            except Exception as e:
                log.error(f"Error in on_stop_callback: {e}")
    
    async def _play_loop(self) -> None:
        """Внутренний цикл воспроизведения placeholder."""
        while not self._stop_event.is_set():
            try:
                # Настройка потока
                stream = AudioPiped(
                    self.placeholder_path,
                    audio_parameters=HighQualityAudio(),
                    additional_ffmpeg_parameters=[
                        "-re",  # Realtime playback
                        "-stream_loop", "-1"  # Бесконечный цикл
                    ]
                )
                
                await self.pytg.join_group_call(self.chat_id, stream)
                
                # Ожидание остановки или проблемы с соединением
                while not self._stop_event.is_set():
                    await asyncio.sleep(5)
                    
                    # Проверка активного звонка
                    try:
                        call = self.pytg.get_call(self.chat_id)
                        if call is None:
                            log.warning("Placeholder call ended unexpectedly, restarting...")
                            break
                    except Exception:
                        break
                
            except Exception as e:
                if not self._stop_event.is_set():
                    log.error(f"Placeholder playback error: {e}")
                    await asyncio.sleep(5)
                else:
                    break
    
    async def restart(self) -> bool:
        """Перезапустить placeholder."""
        await self.stop()
        return await self.start()


class PlaceholderManager:
    """
    Менеджер placeholder для управления несколькими каналами.
    
    Использование:
        manager = PlaceholderManager(pytg)
        await manager.start_placeholder(channel_id)
        await manager.stop_placeholder(channel_id)
    """
    
    def __init__(self, pytg: Optional["PyTgCalls"]):
        self.pytg = pytg
        self._players: dict[Union[int, str], PlaceholderPlayer] = {}
    
    def get_player(self, chat_id: Union[int, str]) -> Optional[PlaceholderPlayer]:
        """Получить player для канала."""
        return self._players.get(chat_id)
    
    async def start_placeholder(
        self,
        chat_id: Union[int, str],
        placeholder_path: Optional[str] = None,
        on_stop_callback: Optional[Callable[[], Awaitable[None]]] = None
    ) -> bool:
        """
        Запустить placeholder для канала.
        
        Args:
            chat_id: ID канала
            placeholder_path: Путь к файлу (опционально)
            on_stop_callback: Callback при остановке
            
        Returns:
            True если запущено успешно
        """
        # Остановить существующий, если есть
        if chat_id in self._players:
            await self.stop_placeholder(chat_id)
        
        player = PlaceholderPlayer(
            pytg=self.pytg,
            chat_id=chat_id,
            placeholder_path=placeholder_path,
            on_stop_callback=on_stop_callback
        )
        
        success = await player.start()
        if success:
            self._players[chat_id] = player
        
        return success
    
    async def stop_placeholder(self, chat_id: Union[int, str]) -> None:
        """Остановить placeholder для канала."""
        player = self._players.pop(chat_id, None)
        if player:
            await player.stop()
    
    def is_playing(self, chat_id: Union[int, str]) -> bool:
        """Проверить, играет ли placeholder для канала."""
        player = self._players.get(chat_id)
        return player.is_playing if player else False
    
    async def stop_all(self) -> None:
        """Остановить все placeholder."""
        for chat_id in list(self._players.keys()):
            await self.stop_placeholder(chat_id)


# Singleton manager instance
_placeholder_manager: Optional[PlaceholderManager] = None


def get_placeholder_manager(pytg: Optional["PyTgCalls"] = None) -> PlaceholderManager:
    """Получить singleton экземпляр PlaceholderManager."""
    global _placeholder_manager
    if _placeholder_manager is None:
        _placeholder_manager = PlaceholderManager(pytg)
    return _placeholder_manager
