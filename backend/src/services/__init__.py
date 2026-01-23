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
- RTMPIngestService: управление RTMP/SRT live stream ingestion (Feature 019)
- WebRTCSignalingService: управление WebRTC сигналингом для guest co-hosting (Feature 019)
- StreamSwitchingService: управление переключением между live и pre-recorded контентом (Feature 019)
- RecordingService: управление записями live streams (Feature 019)
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
    "RTMPIngestService",
    "WebRTCSignalingService",
    "StreamSwitchingService",
    "RecordingService",
]
