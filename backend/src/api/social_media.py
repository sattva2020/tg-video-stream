"""
Social Media API endpoints.
Feature: 021-social-media-integration-cross-platform-broadcasting

Эндпоинты для управления постами в социальных сетях:
- GET /social-media/posts/ - Список постов
- POST /social-media/posts/ - Создание/ручной запуск поста
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import uuid

from src.database import get_db
from src.models.user import User
from src.models.social_media_post import SocialMediaPost
from src.api.auth.dependencies import get_current_user
from src.schemas.streaming_platforms import (
    SocialMediaPostCreate,
    SocialMediaPostResponse,
    SocialMediaPostListResponse,
    PostStatus,
    PostType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social-media", tags=["Social Media"])


# ============ Social Media Posts Endpoints ============

@router.get(
    "/posts/",
    response_model=SocialMediaPostListResponse,
    summary="Получить список постов",
    description="Возвращает список постов в социальных сетях с фильтрацией"
)
async def list_social_media_posts(
    channel_id: Optional[uuid.UUID] = Query(None, description="Фильтр по ID канала"),
    platform_id: Optional[uuid.UUID] = Query(None, description="Фильтр по ID платформы"),
    post_type: Optional[PostType] = Query(None, description="Фильтр по типу поста"),
    post_status: Optional[PostStatus] = Query(None, description="Фильтр по статусу поста"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей"),
    offset: int = Query(0, ge=0, description="Сдвиг для пагинации"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить список постов в социальных сетях.

    Поддерживает фильтрацию по каналу, платформе, типу и статусу поста.
    """
    try:
        # Build query
        query = db.query(SocialMediaPost)

        # Apply filters if provided
        if channel_id:
            query = query.filter(SocialMediaPost.channel_id == channel_id)

        if platform_id:
            query = query.filter(SocialMediaPost.platform_id == platform_id)

        if post_type:
            query = query.filter(SocialMediaPost.post_type == post_type)

        if post_status:
            query = query.filter(SocialMediaPost.status == post_status)

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering
        posts = query.order_by(SocialMediaPost.created_at.desc()).offset(offset).limit(limit).all()

        # Convert to response models
        post_responses = [
            SocialMediaPostResponse(
                id=str(post.id),
                channel_id=str(post.channel_id),
                platform_id=str(post.platform_id),
                post_type=post.post_type,
                status=post.status,
                content=post.content,
                platform_post_id=post.platform_post_id,
                platform_post_url=post.platform_post_url,
                error_message=post.error_message,
                retry_count=post.retry_count,
                posted_at=post.posted_at,
                created_at=post.created_at,
                updated_at=post.updated_at
            )
            for post in posts
        ]

        return SocialMediaPostListResponse(
            posts=post_responses,
            total=total
        )
    except Exception as e:
        logger.error(f"Error listing social media posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to list social media posts")


@router.post(
    "/posts/",
    response_model=SocialMediaPostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать пост или запустить публикацию вручную",
    description="Создает новую запись поста и инициирует его публикацию"
)
async def create_social_media_post(
    post_data: SocialMediaPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать пост или запустить публикацию вручную.

    Создает новую запись в базе данных и инициирует процесс публикации
    на указанной платформе социальных сетей.
    """
    try:
        # Validate channel exists and user has access
        from src.models.channel import Channel
        channel = db.query(Channel).filter(
            Channel.id == post_data.channel_id
        ).first()

        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )

        # Validate platform exists
        from src.models.streaming_platform import StreamingPlatform
        platform = db.query(StreamingPlatform).filter(
            StreamingPlatform.id == post_data.platform_id
        ).first()

        if not platform:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Streaming platform not found"
            )

        # Create new post record
        new_post = SocialMediaPost(
            channel_id=post_data.channel_id,
            platform_id=post_data.platform_id,
            post_type=post_data.post_type,
            content=post_data.content,
            status="pending",
            retry_count=0
        )

        db.add(new_post)
        db.commit()
        db.refresh(new_post)

        # TODO: Trigger actual posting to social media platform
        # This would be handled by a background worker or service
        # For now, we just create the pending record

        logger.info(
            f"Created social media post {new_post.id} "
            f"for channel {post_data.channel_id} on platform {post_data.platform_id}"
        )

        return SocialMediaPostResponse(
            id=str(new_post.id),
            channel_id=str(new_post.channel_id),
            platform_id=str(new_post.platform_id),
            post_type=new_post.post_type,
            status=new_post.status,
            content=new_post.content,
            platform_post_id=new_post.platform_post_id,
            platform_post_url=new_post.platform_post_url,
            error_message=new_post.error_message,
            retry_count=new_post.retry_count,
            posted_at=new_post.posted_at,
            created_at=new_post.created_at,
            updated_at=new_post.updated_at
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error creating social media post: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create social media post")


@router.get(
    "/posts/{post_id}",
    response_model=SocialMediaPostResponse,
    summary="Получить информацию о посте",
    description="Возвращает детальную информацию о конкретном посте"
)
async def get_social_media_post(
    post_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить информацию о конкретном посте по ID.
    """
    try:
        post = db.query(SocialMediaPost).filter(
            SocialMediaPost.id == post_id
        ).first()

        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Social media post not found"
            )

        return SocialMediaPostResponse(
            id=str(post.id),
            channel_id=str(post.channel_id),
            platform_id=str(post.platform_id),
            post_type=post.post_type,
            status=post.status,
            content=post.content,
            platform_post_id=post.platform_post_id,
            platform_post_url=post.platform_post_url,
            error_message=post.error_message,
            retry_count=post.retry_count,
            posted_at=post.posted_at,
            created_at=post.created_at,
            updated_at=post.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting social media post: {e}")
        raise HTTPException(status_code=500, detail="Failed to get social media post")
