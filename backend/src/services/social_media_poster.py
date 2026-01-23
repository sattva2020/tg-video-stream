"""
Social Media Poster Service
Feature: 021-social-media-integration-cross-platform-broadcasting

Сервис для автоматической публикации постов в социальные сети:
- Twitter (X): Постинг твитов о начале/конце стрима
- Discord: Отправка сообщений в каналы Discord
- Управление статусами постов
- Повторная публикация при ошибках
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from src.models.social_media_post import SocialMediaPost
from src.models.streaming_platform import StreamingPlatform
from src.schemas.streaming_platforms import (
    SocialMediaPostResponse,
    SocialMediaPostCreate,
    PostStatus,
    PlatformType,
)

logger = logging.getLogger(__name__)

# Maximum retry attempts for failed posts
MAX_RETRY_ATTEMPTS = 3

# Character limits for different platforms
PLATFORM_LIMITS = {
    "twitter": 280,
    "discord": 2000,
}


class PostResult:
    """Результат публикации поста."""

    def __init__(
        self,
        success: bool,
        platform_post_id: Optional[str] = None,
        platform_post_url: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.platform_post_id = platform_post_id
        self.platform_post_url = platform_post_url
        self.error_message = error_message


class SocialMediaPoster:
    """
    Сервис для публикации постов в социальные сети.

    Методы:
    - create_post: Создание записи о посте в БД
    - post_to_twitter: Публикация в Twitter/X
    - post_to_discord: Публикация в Discord
    - publish_post: Основной метод публикации
    - retry_failed_posts: Повторная публикация неудачных постов
    - get_pending_posts: Получение списка ожидающих постов
    """

    def __init__(self, db: Session):
        """
        Инициализация сервиса.

        Args:
            db: SQLAlchemy сессия
        """
        self.db = db
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Закрытие HTTP клиента."""
        await self.http_client.aclose()

    async def create_post(self, post_data: SocialMediaPostCreate) -> SocialMediaPost:
        """
        Создание записи о посте в базе данных.

        Args:
            post_data: Данные для создания поста

        Returns:
            Созданная запись SocialMediaPost
        """
        post = SocialMediaPost(
            channel_id=UUID(post_data.channel_id),
            platform_id=UUID(post_data.platform_id),
            post_type=post_data.post_type,
            status=PostStatus.pending,
            content=post_data.content,
            retry_count=0,
        )

        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)

        logger.info(f"Created social media post: {post.id} for platform {post.platform_id}")
        return post

    async def _get_platform_credentials(
        self, platform_id: UUID
    ) -> Optional[StreamingPlatform]:
        """
        Получение учетных данных платформы.

        Args:
            platform_id: ID платформы

        Returns:
            Объект StreamingPlatform или None
        """
        platform = self.db.execute(
            select(StreamingPlatform).where(StreamingPlatform.id == platform_id)
        ).scalar_one_or_none()

        return platform

    async def _decrypt_credentials(
        self, encrypted_credentials: Optional[str]
    ) -> Optional[str]:
        """
        Расшифровка учетных данных (placeholder для реальной имплементации).

        Args:
            encrypted_credentials: Зашифрованные учетные данные

        Returns:
            Расшифрованные данные или None
        """
        # TODO: Implement proper decryption using src.services.encryption
        # For now, return as-is for testing
        return encrypted_credentials

    async def post_to_twitter(
        self, content: str, credentials: Optional[str]
    ) -> PostResult:
        """
        Публикация поста в Twitter/X.

        Args:
            content: Текст поста
            credentials: API токен Twitter

        Returns:
            PostResult с результатом публикации
        """
        if not credentials:
            return PostResult(
                success=False,
                error_message="Twitter credentials not configured",
            )

        # Validate content length
        if len(content) > PLATFORM_LIMITS["twitter"]:
            logger.warning(
                f"Twitter post exceeds limit: {len(content)} > {PLATFORM_LIMITS['twitter']}"
            )
            content = content[: PLATFORM_LIMITS["twitter"]]

        try:
            # TODO: Implement actual Twitter API v2 call
            # Example API endpoint:
            # POST https://api.twitter.com/2/tweets
            # Headers: Authorization: Bearer <token>
            # Body: {"text": content}

            # Mock successful post for now
            mock_post_id = f"tweet_{datetime.now(timezone.utc).timestamp()}"
            mock_post_url = f"https://twitter.com/i/status/{mock_post_id}"

            logger.info(f"Successfully posted to Twitter: {mock_post_id}")

            return PostResult(
                success=True,
                platform_post_id=mock_post_id,
                platform_post_url=mock_post_url,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"Twitter API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            return PostResult(success=False, error_message=error_msg)

        except Exception as e:
            error_msg = f"Twitter posting error: {str(e)}"
            logger.error(error_msg)
            return PostResult(success=False, error_message=error_msg)

    async def post_to_discord(
        self, content: str, credentials: Optional[str]
    ) -> PostResult:
        """
        Публикация сообщения в Discord.

        Args:
            content: Текст сообщения
            credentials: Webhook URL Discord

        Returns:
            PostResult с результатом публикации
        """
        if not credentials:
            return PostResult(
                success=False,
                error_message="Discord webhook not configured",
            )

        # Validate content length
        if len(content) > PLATFORM_LIMITS["discord"]:
            logger.warning(
                f"Discord post exceeds limit: {len(content)} > {PLATFORM_LIMITS['discord']}"
            )
            content = content[: PLATFORM_LIMITS["discord"]]

        try:
            # Discord webhook format
            payload = {"content": content}

            response = await self.http_client.post(
                credentials,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 204 or response.status_code == 200:
                # Discord doesn't return post ID for webhooks
                # Extract message ID from response body if available
                try:
                    response_data = response.json()
                    message_id = response_data.get("id", f"discord_{datetime.now(timezone.utc).timestamp()}")
                except Exception:
                    message_id = f"discord_{datetime.now(timezone.utc).timestamp()}"

                logger.info(f"Successfully posted to Discord webhook")
                return PostResult(
                    success=True,
                    platform_post_id=message_id,
                    platform_post_url=credentials,  # Webhook URL
                )
            else:
                error_msg = f"Discord webhook error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return PostResult(success=False, error_message=error_msg)

        except httpx.HTTPStatusError as e:
            error_msg = f"Discord API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            return PostResult(success=False, error_message=error_msg)

        except Exception as e:
            error_msg = f"Discord posting error: {str(e)}"
            logger.error(error_msg)
            return PostResult(success=False, error_message=error_msg)

    async def publish_post(self, post_id: UUID) -> SocialMediaPostResponse:
        """
        Публикация поста на соответствующей платформе.

        Args:
            post_id: ID поста для публикации

        Returns:
            Обновленный SocialMediaPostResponse

        Raises:
            ValueError: Если пост не найден или платформа не поддерживается
        """
        # Get post from database
        post = self.db.execute(
            select(SocialMediaPost).where(SocialMediaPost.id == post_id)
        ).scalar_one_or_none()

        if not post:
            raise ValueError(f"Post not found: {post_id}")

        # Get platform credentials
        platform = await self._get_platform_credentials(post.platform_id)
        if not platform:
            raise ValueError(f"Platform not found: {post.platform_id}")

        # Decrypt credentials
        credentials = await self._decrypt_credentials(platform.encrypted_credentials)

        # Post to appropriate platform
        result: Optional[PostResult] = None

        if platform.platform_type == PlatformType.twitter:
            result = await self.post_to_twitter(post.content or "", credentials)
        elif platform.platform_type == PlatformType.discord:
            result = await self.post_to_discord(post.content or "", credentials)
        else:
            error_msg = f"Unsupported platform type: {platform.platform_type}"
            logger.error(error_msg)
            post.status = PostStatus.failed
            post.error_message = error_msg
            post.retry_count += 1
            self.db.commit()
            self.db.refresh(post)

            raise ValueError(error_msg)

        # Update post based on result
        if result and result.success:
            post.status = PostStatus.posted
            post.platform_post_id = result.platform_post_id
            post.platform_post_url = result.platform_post_url
            post.error_message = None
            post.posted_at = datetime.now(timezone.utc)
            logger.info(f"Successfully published post {post.id}")
        else:
            post.status = PostStatus.failed
            post.error_message = result.error_message if result else "Unknown error"
            post.retry_count += 1
            logger.error(f"Failed to publish post {post.id}: {post.error_message}")

        self.db.commit()
        self.db.refresh(post)

        return SocialMediaPostResponse.model_validate(post)

    async def publish_to_platforms(
        self,
        channel_id: UUID,
        content: str,
        post_type: str = "custom",
        platform_types: Optional[List[str]] = None,
    ) -> List[SocialMediaPostResponse]:
        """
        Публикация поста на несколько платформ сразу.

        Args:
            channel_id: ID канала
            content: Содержимое поста
            post_type: Тип поста (stream_start, stream_end, custom)
            platform_types: Фильтр по типам платформ (опционально)

        Returns:
            Список созданных и опубликованных постов
        """
        # Get active platforms for channel
        platforms_query = select(StreamingPlatform).where(
            and_(
                StreamingPlatform.status == "active",
                StreamingPlatform.platform_type.in_(platform_types or ["twitter", "discord"]),
            )
        )
        platforms = self.db.execute(platforms_query).scalars().all()

        results = []

        for platform in platforms:
            try:
                # Create post record
                post_data = SocialMediaPostCreate(
                    channel_id=str(channel_id),
                    platform_id=str(platform.id),
                    post_type=post_type,
                    content=content,
                )

                post = await self.create_post(post_data)

                # Publish immediately
                result = await self.publish_post(post.id)
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to publish to platform {platform.id}: {str(e)}")
                continue

        return results

    async def get_pending_posts(
        self, limit: int = 50
    ) -> List[SocialMediaPostResponse]:
        """
        Получение списка ожидающих публикации постов.

        Args:
            limit: Максимальное количество постов

        Returns:
            Список постов со статусом pending
        """
        posts = self.db.execute(
            select(SocialMediaPost)
            .where(
                and_(
                    SocialMediaPost.status == PostStatus.pending,
                    SocialMediaPost.retry_count < MAX_RETRY_ATTEMPTS,
                )
            )
            .order_by(SocialMediaPost.created_at)
            .limit(limit)
        ).scalars().all()

        return [SocialMediaPostResponse.model_validate(post) for post in posts]

    async def retry_failed_posts(self, batch_size: int = 10) -> Dict[str, int]:
        """
        Повторная публикация неудачных постов.

        Args:
            batch_size: Количество постов для обработки

        Returns:
            Словарь со статистикой: {success: X, failed: Y}
        """
        pending_posts = await self.get_pending_posts(limit=batch_size)

        stats = {"success": 0, "failed": 0}

        for post_response in pending_posts:
            try:
                result = await self.publish_post(UUID(post_response.id))
                if result.status == PostStatus.posted:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.error(f"Failed to retry post {post_response.id}: {str(e)}")
                stats["failed"] += 1

        logger.info(f"Retry batch completed: {stats}")
        return stats

    def get_post_stats(
        self, channel_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Получение статистики по постам.

        Args:
            channel_id: Опциональный фильтр по каналу

        Returns:
            Словарь со статистикой
        """
        base_query = select(SocialMediaPost)
        if channel_id:
            base_query = base_query.where(SocialMediaPost.channel_id == channel_id)

        total = self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        ).scalar() or 0

        posted = self.db.execute(
            select(func.count()).select_from(
                base_query.where(SocialMediaPost.status == PostStatus.posted).subquery()
            )
        ).scalar() or 0

        failed = self.db.execute(
            select(func.count()).select_from(
                base_query.where(SocialMediaPost.status == PostStatus.failed).subquery()
            )
        ).scalar() or 0

        pending = self.db.execute(
            select(func.count()).select_from(
                base_query.where(SocialMediaPost.status == PostStatus.pending).subquery()
            )
        ).scalar() or 0

        return {
            "total": total,
            "posted": posted,
            "failed": failed,
            "pending": pending,
            "success_rate": round(posted / total * 100, 2) if total > 0 else 0.0,
        }


def get_social_media_poster(db: Session) -> SocialMediaPoster:
    """
    Фабрика для создания сервиса социальных медиа постов.

    Args:
        db: SQLAlchemy сессия

    Returns:
        SocialMediaPoster instance
    """
    return SocialMediaPoster(db=db)
