"""
Services модуль для обработки бизнес-логики.

Содержит:
- PlaybackService: управление воспроизведением (скорость, pitch, seek)
- RadioService: управление радио-потоками
- QueueService: приоритетные очереди (Redis sorted sets)
- LyricsService: получение текстов песен (Genius API)
- ShazamService: распознавание музыки
- SchedulerService: запланированное воспроизведение плейлистов
- BackupService: автоматизированные резервные копии
- ChannelService: управление мульти-канальной трансляцией
- EncodingProfileService: валидация кодеков и управление профилями кодирования
"""

__all__ = [
    "PlaybackService",
    "RadioService",
    "QueueService",
    "LyricsService",
    "ShazamService",
    "SchedulerService",
    "BackupService",
    "ChannelService",
    "EncodingProfileService",
]
