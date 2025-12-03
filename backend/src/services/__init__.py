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
]
