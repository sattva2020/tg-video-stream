"""
Chat Aggregation API endpoints.
Feature: 021-social-media-integration-cross-platform-broadcasting

Эндпоинты для агрегации чатов с разных платформ:
- GET /chat/messages/ - Получить агрегированные сообщения чата
- WS /chat/ws - WebSocket для real-time обновлений чата
"""

import asyncio
import json
import logging
from typing import Optional, List, Set, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import uuid

from src.database import get_db
from src.models.user import User
from src.models.chat_message import ChatMessage
from src.models.channel import Channel
from src.api.auth.dependencies import get_current_user
from src.schemas.streaming_platforms import (
    ChatMessageResponse,
    ChatMessageListResponse,
    ChatMessageAggregatedResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat Aggregation"])


# ============ WebSocket Connection Manager for Chat ============

class ChatConnectionManager:
    """Менеджер WebSocket соединений для чата."""

    def __init__(self):
        # channel_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel_id: str):
        """Принять соединение и добавить в группу канала."""
        await websocket.accept()
        async with self._lock:
            if channel_id not in self.active_connections:
                self.active_connections[channel_id] = set()
            self.active_connections[channel_id].add(websocket)
        logger.info(f"Chat WebSocket connected: channel={channel_id}, total={self._total_connections()}")

    async def disconnect(self, websocket: WebSocket, channel_id: str):
        """Удалить соединение из группы."""
        async with self._lock:
            if channel_id in self.active_connections:
                self.active_connections[channel_id].discard(websocket)
                if not self.active_connections[channel_id]:
                    del self.active_connections[channel_id]
        logger.info(f"Chat WebSocket disconnected: channel={channel_id}, total={self._total_connections()}")

    async def broadcast_to_channel(self, channel_id: str, message: dict):
        """Отправить сообщение всем подключенным к каналу."""
        async with self._lock:
            connections = self.active_connections.get(channel_id, set()).copy()

        if not connections:
            return

        data = json.dumps(message, default=str)
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_text(data)
            except Exception as e:
                logger.warning(f"Failed to send chat message to websocket: {e}")
                disconnected.append(websocket)

        # Cleanup disconnected
        for ws in disconnected:
            await self.disconnect(ws, channel_id)

    def _total_connections(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())


# Глобальный менеджер соединений для чата
chat_manager = ChatConnectionManager()


# ============ Chat Messages Endpoints ============

@router.get(
    "/messages/",
    response_model=ChatMessageAggregatedResponse,
    summary="Получить агрегированные сообщения чата",
    description="Возвращает сообщения чата со всех платформ для указанного канала"
)
async def get_chat_messages(
    channel_id: uuid.UUID = Query(..., description="ID канала"),
    platform_id: Optional[uuid.UUID] = Query(None, description="Фильтр по ID платформы"),
    limit: int = Query(100, ge=1, le=500, description="Количество сообщений"),
    offset: int = Query(0, ge=0, description="Сдвиг для пагинации"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить агрегированные сообщения чата.

    Возвращает сообщения со всех подключенных платформ (Telegram, YouTube, Twitch и т.д.)
    для указанного канала. Сообщения сортируются по времени отправки.
    """
    try:
        # Validate channel exists
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            raise HTTPException(
                status_code=404,
                detail="Channel not found"
            )

        # Build query
        query = db.query(ChatMessage).filter(ChatMessage.channel_id == channel_id)

        # Apply platform filter if provided
        if platform_id:
            query = query.filter(ChatMessage.platform_id == platform_id)

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering (newest first)
        messages = query.order_by(
            ChatMessage.message_timestamp.desc()
        ).offset(offset).limit(limit).all()

        # Get unique platforms
        platforms = list(set(
            str(msg.platform_id) for msg in messages
        ))

        # Convert to response models
        message_responses = [
            ChatMessageResponse(
                id=str(msg.id),
                platform_id=str(msg.platform_id),
                channel_id=str(msg.channel_id),
                platform_message_id=msg.platform_message_id,
                author_name=msg.author_name,
                author_display_name=msg.author_display_name,
                content=msg.content,
                message_timestamp=msg.message_timestamp,
                author_color=msg.author_color,
                metadata=json.loads(msg.metadata) if msg.metadata else None,
                created_at=msg.created_at
            )
            for msg in messages
        ]

        return ChatMessageAggregatedResponse(
            channel_id=str(channel_id),
            messages=message_responses,
            platforms=platforms,
            total=total
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat messages")


@router.get(
    "/messages/{message_id}",
    response_model=ChatMessageResponse,
    summary="Получить конкретное сообщение",
    description="Возвращает детальную информацию о сообщении чата"
)
async def get_chat_message(
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить конкретное сообщение чата по ID.
    """
    try:
        message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()

        if not message:
            raise HTTPException(
                status_code=404,
                detail="Chat message not found"
            )

        return ChatMessageResponse(
            id=str(message.id),
            platform_id=str(message.platform_id),
            channel_id=str(message.channel_id),
            platform_message_id=message.platform_message_id,
            author_name=message.author_name,
            author_display_name=message.author_display_name,
            content=message.content,
            message_timestamp=message.message_timestamp,
            author_color=message.author_color,
            metadata=json.loads(message.metadata) if message.metadata else None,
            created_at=message.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat message: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat message")


# ============ WebSocket Endpoint for Real-time Chat ============

@router.websocket("/ws")
async def websocket_chat(
    websocket: WebSocket,
    channel_id: str = Query(..., description="ID канала для подписки на чат"),
):
    """
    WebSocket endpoint для получения сообщений чата в реальном времени.

    Query params:
        - channel_id: ID канала для подписки на сообщения чата

    Сообщения от сервера:
        - {"type": "message", "data": {...}} - новое сообщение в чате
        - {"type": "messages_batch", "data": [...]} - пакет сообщений
        - {"type": "ping"} - keepalive

    Сообщения от клиента:
        - {"type": "ping"} - keepalive
        - {"type": "refresh"} - запросить последние сообщения
    """
    await chat_manager.connect(websocket, channel_id)

    try:
        # Send initial recent messages
        await _send_recent_messages(websocket, channel_id)

        # Listen for messages from client
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message.get("type") == "refresh":
                    await _send_recent_messages(websocket, channel_id)

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Chat WebSocket error: {e}")
    finally:
        await chat_manager.disconnect(websocket, channel_id)


async def _send_recent_messages(websocket: WebSocket, channel_id: str):
    """Отправить последние сообщения через WebSocket."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        # Get last 50 messages
        messages = db.query(ChatMessage).filter(
            ChatMessage.channel_id == uuid.UUID(channel_id)
        ).order_by(
            ChatMessage.message_timestamp.desc()
        ).limit(50).all()

        message_data = [
            {
                "id": str(msg.id),
                "platform_id": str(msg.platform_id),
                "channel_id": str(msg.channel_id),
                "platform_message_id": msg.platform_message_id,
                "author_name": msg.author_name,
                "author_display_name": msg.author_display_name,
                "content": msg.content,
                "message_timestamp": msg.message_timestamp.isoformat(),
                "author_color": msg.author_color,
                "metadata": json.loads(msg.metadata) if msg.metadata else None,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]

        await websocket.send_text(json.dumps({
            "type": "messages_batch",
            "data": message_data
        }, default=str))
    except ValueError:
        # Invalid UUID
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Invalid channel_id format"
        }))
    except Exception as e:
        logger.error(f"Error sending recent messages: {e}")
    finally:
        db.close()


# ============ Functions for notifying clients (called from other modules) ============

async def notify_chat_message(message: ChatMessage):
    """
    Уведомить клиентов о новом сообщении в чате.

    Вызывается из сервиса агрегации чата при получении нового сообщения.
    """
    try:
        message_data = {
            "id": str(message.id),
            "platform_id": str(message.platform_id),
            "channel_id": str(message.channel_id),
            "platform_message_id": message.platform_message_id,
            "author_name": message.author_name,
            "author_display_name": message.author_display_name,
            "content": message.content,
            "message_timestamp": message.message_timestamp.isoformat(),
            "author_color": message.author_color,
            "metadata": json.loads(message.metadata) if message.metadata else None,
            "created_at": message.created_at.isoformat()
        }

        await chat_manager.broadcast_to_channel(
            str(message.channel_id),
            {
                "type": "message",
                "data": message_data
            }
        )
    except Exception as e:
        logger.error(f"Error notifying chat message: {e}")


async def notify_chat_messages_batch(channel_id: str, messages: List[ChatMessage]):
    """
    Уведомить клиентов о пакете новых сообщений.

    Используется при периодической агрегации сообщений.
    """
    try:
        message_data = [
            {
                "id": str(msg.id),
                "platform_id": str(msg.platform_id),
                "channel_id": str(msg.channel_id),
                "platform_message_id": msg.platform_message_id,
                "author_name": msg.author_name,
                "author_display_name": msg.author_display_name,
                "content": msg.content,
                "message_timestamp": msg.message_timestamp.isoformat(),
                "author_color": msg.author_color,
                "metadata": json.loads(msg.metadata) if msg.metadata else None,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]

        await chat_manager.broadcast_to_channel(
            channel_id,
            {
                "type": "messages_batch",
                "data": message_data
            }
        )
    except Exception as e:
        logger.error(f"Error notifying chat messages batch: {e}")
