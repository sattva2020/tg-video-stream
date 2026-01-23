"""
Services модуль для обработки бизнес-логики.

Содержит:
- PlaybackService: управление воспроизведением (скорость, pitch, seek)
- RadioService: управление радио-потоками
- QueueService: приоритетные очереди (Redis sorted sets)
- PollService: управление интерактивными опросами
- QAService: управление вопросами и ответами (Q&A сессии)
- ModerationService: фильтрация контента и модерация
- LyricsService: получение текстов песен (Genius API)
- ShazamService: распознавание музыки
- SchedulerService: запланированное воспроизведение плейлистов
- BackupService: автоматизированные резервные копии
- ChannelService: управление мульти-канальной трансляцией
- InteractionAnalyticsService: аналитика взаимодействий (polls, Q&A, reactions, chat)
- TelegramChatService: интеграция Telegram чата с stream overlay
"""

__all__ = [
    "PlaybackService",
    "RadioService",
    "QueueService",
    "PollService",
    "QAService",
    "ModerationService",
    "LyricsService",
    "ShazamService",
    "SchedulerService",
    "BackupService",
    "ChannelService",
    "InteractionAnalyticsService",
    "TelegramChatService",
]
