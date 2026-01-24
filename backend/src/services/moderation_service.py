"""
Moderation Service - фильтрация контента и модерация

Сервис обеспечивает:
- Автоматическую фильтрацию неуместного контента
- Проверку текста на запрещенные слова/паттерны
- Ручную модерацию (одобрение/отклонение)
- Пометку контента для проверки
- Redis кэш для blacklist слов и паттернов

Storage: PostgreSQL (обновление статусов), Redis (кэш blacklist)
"""

import re
from typing import Optional, List, Set, Tuple
from enum import Enum
import logging

import redis.asyncio as redis

from src.config import settings
from src.models.interaction import EmojiReaction

logger = logging.getLogger(__name__)


class ModerationServiceError(Exception):
    """Базовое исключение для ошибок ModerationService."""
    pass


class ContentNotAllowedError(ModerationServiceError):
    """Контент нарушает правила и не может быть опубликован."""
    pass


class ContentAlreadyModeratedError(ModerationServiceError):
    """Контент уже прошел модерацию."""
    pass


class ModerationAction(str, Enum):
    """Действия модерации."""
    AUTO_FILTER = "auto_filter"       # Автоматическая фильтрация
    MANUAL_APPROVE = "manual_approve"  # Ручное одобрение
    MANUal_REJECT = "manual_reject"   # Ручное отклонение
    FLAG_FOR_REVIEW = "flag_review"   # Пометка для проверки


class ModerationResult:
    """Результат проверки контента."""
    def __init__(
        self,
        is_allowed: bool,
        reason: Optional[str] = None,
        action: ModerationAction = ModerationAction.AUTO_FILTER,
        matched_patterns: Optional[List[str]] = None
    ):
        self.is_allowed = is_allowed
        self.reason = reason
        self.action = action
        self.matched_patterns = matched_patterns or []

    def __repr__(self) -> str:
        return f"<ModerationResult(allowed={self.is_allowed}, reason='{self.reason}')>"


class ModerationService:
    """
    Сервис модерации контента.

    Обеспечивает автоматическую фильтрацию и ручную модерацию:
    - Проверка текста на blacklist слова/паттерны (Redis)
    - Фильтрация эмодзи-реакций и чат-сообщений
    - Модерация вопросов Q&A
    - Кэширование blacklist в Redis

    Attributes:
        redis_url: URL подключения к Redis
        default_blacklist: Набор запрещенных слов по умолчанию
    """

    # Redis key patterns
    BLACKLIST_KEY = "moderation:blacklist"
    FLAGGED_USERS_KEY = "moderation:flagged_users"

    # Ограничения
    MAX_CONTENT_LENGTH = 5000
    MAX_LINKS_PER_MESSAGE = 3

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_blacklist: Optional[Set[str]] = None
    ):
        """
        Инициализация ModerationService.

        Args:
            redis_url: URL Redis (по умолчанию из settings)
            default_blacklist: Набор запрещенных слов по умолчанию
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.default_blacklist = default_blacklist or self._get_default_blacklist()
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Получение Redis клиента с lazy initialization."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._redis

    async def close(self) -> None:
        """Закрытие Redis соединения."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    @staticmethod
    def _get_default_blacklist() -> Set[str]:
        """
        Получить набор запрещенных слов по умолчанию.

        Returns:
            Set слов/паттернов для фильтрации
        """
        # Базовый blacklist (может быть расширен через Redis)
        return {
            # Примеры запрещенных слов (должны быть настроены администратором)
            # Это placeholder - реальные слова должны быть в конфиге
        }

    # ========== Blacklist Management ==========

    async def get_blacklist(self) -> Set[str]:
        """
        Получить blacklist слов из Redis или defaults.

        Returns:
            Set запрещенных слов/паттернов
        """
        r = await self._get_redis()

        try:
            # Попытка получить из Redis
            cached = await r.smembers(self.BLACKLIST_KEY)
            if cached:
                logger.debug(f"Загружен blacklist из Redis: {len(cached)} слов")
                return set(cached)
        except Exception as e:
            logger.warning(f"Ошибка загрузки blacklist из Redis: {e}")

        # Возвращаем defaults
        logger.debug("Используется blacklist по умолчанию")
        return self.default_blacklist

    async def add_to_blacklist(self, word: str) -> None:
        """
        Добавить слово в blacklist.

        Args:
            word: Слово или паттерн для фильтрации
        """
        r = await self._get_redis()
        await r.sadd(self.BLACKLIST_KEY, word.lower().strip())
        logger.info(f"Добавлено в blacklist: '{word}'")

    async def remove_from_blacklist(self, word: str) -> None:
        """
        Удалить слово из blacklist.

        Args:
            word: Слово или паттерн
        """
        r = await self._get_redis()
        await r.srem(self.BLACKLIST_KEY, word.lower().strip())
        logger.info(f"Удалено из blacklist: '{word}'")

    # ========== Content Checking ==========

    async def check_text(
        self,
        text: str,
        blacklist: Optional[Set[str]] = None
    ) -> ModerationResult:
        """
        Проверить текст на наличие запрещенного контента.

        Args:
            text: Проверяемый текст
            blacklist: Опциональный набор запрещенных слов

        Returns:
            ModerationResult с результатом проверки
        """
        if not text or not text.strip():
            return ModerationResult(
                is_allowed=True,
                reason="Empty content"
            )

        # Проверка длины
        if len(text) > self.MAX_CONTENT_LENGTH:
            return ModerationResult(
                is_allowed=False,
                reason=f"Content too long (max {self.MAX_CONTENT_LENGTH} chars)",
                action=ModerationAction.AUTO_FILTER
            )

        # Получаем blacklist
        if blacklist is None:
            blacklist = await self.get_blacklist()

        if not blacklist:
            # Нет blacklist - разрешаем все
            return ModerationResult(is_allowed=True)

        # Приводим к нижнему регистру для проверки
        text_lower = text.lower()
        matched_patterns = []

        # Проверяем каждое слово/паттерн
        for pattern in blacklist:
            if pattern in text_lower:
                matched_patterns.append(pattern)

        if matched_patterns:
            return ModerationResult(
                is_allowed=False,
                reason=f"Contains forbidden content: {', '.join(matched_patterns[:3])}",
                action=ModerationAction.AUTO_FILTER,
                matched_patterns=matched_patterns
            )

        # Проверка на подозрительные ссылки (много URL в одном сообщении)
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, text, re.IGNORECASE)
        if len(urls) > self.MAX_LINKS_PER_MESSAGE:
            return ModerationResult(
                is_allowed=False,
                reason=f"Too many links ({len(urls)} > {self.MAX_LINKS_PER_MESSAGE})",
                action=ModerationAction.AUTO_FILTER
            )

        return ModerationResult(is_allowed=True)

    async def should_auto_filter(
        self,
        text: str,
        user_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверить, должен ли контент быть автоотфильтрован.

        Args:
            text: Проверяемый текст
            user_id: ID пользователя (для проверки flagged users)

        Returns:
            Tuple (should_filter, reason)
        """
        result = await self.check_text(text)

        if not result.is_allowed:
            return True, result.reason

        # Проверка flagged users
        if user_id:
            r = await self._get_redis()
            is_flagged = await r.sismember(self.FLAGGED_USERS_KEY, str(user_id))
            if is_flagged:
                return True, "User is flagged for moderation"

        return False, None

    # ========== Emoji Reaction Moderation ==========

    async def filter_reaction(
        self,
        reaction: EmojiReaction
    ) -> ModerationResult:
        """
        Проверить и отфильтровать эмодзи-реакцию.

        Args:
            reaction: EmojiReaction ORM модель

        Returns:
            ModerationResult
        """
        # Эмодзи обычно не требуют текстовой проверки
        # Но может иметь custom логику (например, определенные эмодзи)

        # Здесь можно добавить логику для запрета определенных эмодзи
        # Например, через набор запрещенных эмодзи

        return ModerationResult(is_allowed=True)

    async def approve_reaction(self, reaction_id: str) -> None:
        """
        Одобрить реакцию (ручная модерация).

        Args:
            reaction_id: UUID реакции
        """
        # Логика одобрения должна быть реализована в сервисе
        # Здесь только пример интерфейса
        logger.info(f"Одобрена реакция: {reaction_id}")

    async def reject_reaction(
        self,
        reaction_id: str,
        reason: str
    ) -> None:
        """
        Отклонить реакцию (ручная модерация).

        Args:
            reaction_id: UUID реакции
            reason: Причина отклонения
        """
        logger.info(f"Отклонена реакция: {reaction_id}, причина: {reason}")

    # ========== Chat Message Moderation ==========

    async def filter_chat_message(
        self,
        content: str,
        user_id: Optional[int] = None
    ) -> ModerationResult:
        """
        Проверить и отфильтровать чат-сообщение.

        Args:
            content: Текст сообщения
            user_id: ID пользователя

        Returns:
            ModerationResult
        """
        should_filter, reason = await self.should_auto_filter(content, user_id)

        if should_filter:
            return ModerationResult(
                is_allowed=False,
                reason=reason,
                action=ModerationAction.AUTO_FILTER
            )

        return ModerationResult(is_allowed=True)

    async def approve_message(self, message_id: str) -> None:
        """
        Одобрить сообщение (ручная модерация).

        Args:
            message_id: UUID сообщения
        """
        logger.info(f"Одобрено сообщение: {message_id}")

    async def reject_message(
        self,
        message_id: str,
        reason: str
    ) -> None:
        """
        Отклонить сообщение (ручная модерация).

        Args:
            message_id: UUID сообщения
            reason: Причина отклонения
        """
        logger.info(f"Отклонено сообщение: {message_id}, причина: {reason}")

    # ========== Q&A Question Moderation ==========

    async def filter_question(
        self,
        content: str,
        user_id: Optional[int] = None
    ) -> ModerationResult:
        """
        Проверить и отфильтровать вопрос Q&A.

        Args:
            content: Текст вопроса
            user_id: ID пользователя

        Returns:
            ModerationResult
        """
        should_filter, reason = await self.should_auto_filter(content, user_id)

        if should_filter:
            return ModerationResult(
                is_allowed=False,
                reason=reason,
                action=ModerationAction.AUTO_FILTER
            )

        return ModerationResult(is_allowed=True)

    async def approve_question(self, question_id: str) -> None:
        """
        Одобрить вопрос (ручная модерация).

        Args:
            question_id: UUID вопроса
        """
        logger.info(f"Одобрен вопрос: {question_id}")

    async def reject_question(
        self,
        question_id: str,
        reason: str
    ) -> None:
        """
        Отклонить вопрос (ручная модерация).

        Args:
            question_id: UUID вопроса
            reason: Причина отклонения
        """
        logger.info(f"Отклонен вопрос: {question_id}, причина: {reason}")

    async def pin_question(self, question_id: str) -> None:
        """
        Закрепить вопрос (важный).

        Args:
            question_id: UUID вопроса
        """
        logger.info(f"Закреплен вопрос: {question_id}")

    # ========== User Moderation ==========

    async def flag_user(self, user_id: int, reason: str) -> None:
        """
        Пометить пользователя для модерации.

        Args:
            user_id: ID пользователя
            reason: Причина пометки
        """
        r = await self._get_redis()
        await r.sadd(self.FLAGGED_USERS_KEY, str(user_id))
        logger.warning(f"Пользователь {user_id} помечен: {reason}")

    async def unflag_user(self, user_id: int) -> None:
        """
        Снять пометку с пользователя.

        Args:
            user_id: ID пользователя
        """
        r = await self._get_redis()
        await r.srem(self.FLAGGED_USERS_KEY, str(user_id))
        logger.info(f"Снята пометка с пользователя {user_id}")

    async def is_user_flagged(self, user_id: int) -> bool:
        """
        Проверить, помечен ли пользователь.

        Args:
            user_id: ID пользователя

        Returns:
            True если пользователь помечен
        """
        r = await self._get_redis()
        return await r.sismember(self.FLAGGED_USERS_KEY, str(user_id))

    # ========== Batch Operations ==========

    async def filter_multiple_texts(
        self,
        texts: List[str],
        user_id: Optional[int] = None
    ) -> List[ModerationResult]:
        """
        Проверить несколько текстов пакетом.

        Args:
            texts: Список текстов для проверки
            user_id: ID пользователя

        Returns:
            List ModerationResult для каждого текста
        """
        results = []

        for text in texts:
            should_filter, reason = await self.should_auto_filter(
                text,
                user_id
            )

            if should_filter:
                results.append(ModerationResult(
                    is_allowed=False,
                    reason=reason,
                    action=ModerationAction.AUTO_FILTER
                ))
            else:
                results.append(ModerationResult(is_allowed=True))

        return results


# Singleton instance
_moderation_service: Optional[ModerationService] = None


def get_moderation_service() -> ModerationService:
    """Получить singleton экземпляр ModerationService."""
    global _moderation_service
    if _moderation_service is None:
        _moderation_service = ModerationService()
    return _moderation_service


async def shutdown_moderation_service() -> None:
    """Закрыть ModerationService при завершении приложения."""
    global _moderation_service
    if _moderation_service is not None:
        await _moderation_service.close()
        _moderation_service = None
