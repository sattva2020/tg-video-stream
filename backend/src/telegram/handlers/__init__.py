"""
Telegram event handlers package.

Exports all handler registration functions for easy importing.

Integration with RateLimitQueueService:
All handlers can use telegram_api_queue for API calls that benefit from:
- Priority-based execution (stream control > metadata > background)
- Automatic rate limit handling and retry logic
- Batch processing for efficiency
- Multi-account load distribution

Usage patterns:
1. Immediate responses: Use direct client calls (message.reply_text)
2. Background tasks: Use telegram_api_queue.execute_api_call()
3. Bulk operations: Use telegram_api_queue.enqueue() + process_queue()
"""

from .audio_recognition import register_audio_handlers

__all__ = [
    "register_audio_handlers",
]
