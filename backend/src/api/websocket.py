"""
WebSocket API для real-time обновлений плейлиста и статуса стрима.

Клиенты подключаются к /api/ws/playlist и получают обновления в реальном времени
вместо polling каждые 3 секунды.
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional, TYPE_CHECKING
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import uuid

if TYPE_CHECKING:
    from src.models.playlist import PlaylistItem

router = APIRouter()
log = logging.getLogger("websocket")


class ConnectionManager:
    """Менеджер WebSocket соединений с поддержкой каналов."""
    
    def __init__(self):
        # channel_id -> set of websockets
        self.active_connections: Dict[Optional[str], Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, channel_id: Optional[str] = None):
        """Принять соединение и добавить в группу канала."""
        await websocket.accept()
        async with self._lock:
            if channel_id not in self.active_connections:
                self.active_connections[channel_id] = set()
            self.active_connections[channel_id].add(websocket)
        log.info(f"WebSocket connected: channel={channel_id}, total={self._total_connections()}")
    
    async def disconnect(self, websocket: WebSocket, channel_id: Optional[str] = None):
        """Удалить соединение из группы."""
        async with self._lock:
            if channel_id in self.active_connections:
                self.active_connections[channel_id].discard(websocket)
                if not self.active_connections[channel_id]:
                    del self.active_connections[channel_id]
        log.info(f"WebSocket disconnected: channel={channel_id}, total={self._total_connections()}")
    
    async def broadcast_to_channel(self, channel_id: Optional[str], message: dict):
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
                log.warning(f"Failed to send to websocket: {e}")
                disconnected.append(websocket)
        
        # Cleanup disconnected
        for ws in disconnected:
            await self.disconnect(ws, channel_id)
    
    async def broadcast_all(self, message: dict):
        """Отправить сообщение всем подключенным клиентам."""
        async with self._lock:
            all_channels = list(self.active_connections.keys())
        
        for channel_id in all_channels:
            await self.broadcast_to_channel(channel_id, message)
    
    def _total_connections(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())


# Глобальный менеджер соединений
manager = ConnectionManager()


def _serialize_playlist_item(item) -> dict:
    """Сериализовать элемент плейлиста для отправки через WebSocket."""
    return {
        "id": str(item.id),
        "url": item.url,
        "title": item.title,
        "type": item.type,
        "position": item.position,
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "status": item.status if hasattr(item, 'status') else 'queued',
        "duration": item.duration if hasattr(item, 'duration') else None,
    }


@router.websocket("/playlist")
async def websocket_playlist(
    websocket: WebSocket,
    channel_id: Optional[str] = Query(None),
):
    """
    WebSocket endpoint для получения обновлений плейлиста в реальном времени.
    
    Query params:
        - channel_id: опциональный ID канала для фильтрации
    
    Сообщения от сервера:
        - {"type": "playlist", "data": [...]} - полный список плейлиста
        - {"type": "item_added", "data": {...}} - добавлен новый элемент
        - {"type": "item_removed", "item_id": "..."} - удален элемент
        - {"type": "item_updated", "data": {...}} - обновлен статус элемента
        - {"type": "stream_status", "status": "online|offline|error"} - статус стрима
    
    Сообщения от клиента:
        - {"type": "ping"} - keepalive
        - {"type": "refresh"} - запросить полный список
    """
    await manager.connect(websocket, channel_id)
    
    try:
        # Отправить начальный список плейлиста
        await _send_full_playlist(websocket, channel_id)
        
        # Слушать сообщения от клиента
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message.get("type") == "refresh":
                    await _send_full_playlist(websocket, channel_id)
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket, channel_id)


async def _send_full_playlist(websocket: WebSocket, channel_id: Optional[str]):
    """Отправить полный список плейлиста через WebSocket."""
    # Lazy import to avoid circular dependencies
    from database import SessionLocal
    from src.models.playlist import PlaylistItem
    
    db = SessionLocal()
    try:
        query = db.query(PlaylistItem)
        if channel_id:
            try:
                channel_uuid = uuid.UUID(channel_id)
                query = query.filter(PlaylistItem.channel_id == channel_uuid)
            except ValueError:
                pass
        
        items = query.order_by(PlaylistItem.position.asc(), PlaylistItem.created_at.asc()).all()
        
        await websocket.send_text(json.dumps({
            "type": "playlist",
            "data": [_serialize_playlist_item(item) for item in items]
        }, default=str))
    finally:
        db.close()


# === Функции для уведомления клиентов (вызываются из других модулей) ===

async def notify_item_added(item, channel_id: Optional[str] = None):
    """Уведомить клиентов о добавлении элемента."""
    await manager.broadcast_to_channel(channel_id, {
        "type": "item_added",
        "data": _serialize_playlist_item(item)
    })


async def notify_item_removed(item_id: str, channel_id: Optional[str] = None):
    """Уведомить клиентов об удалении элемента."""
    await manager.broadcast_to_channel(channel_id, {
        "type": "item_removed",
        "item_id": item_id
    })


async def notify_item_updated(item, channel_id: Optional[str] = None):
    """Уведомить клиентов об обновлении элемента."""
    await manager.broadcast_to_channel(channel_id, {
        "type": "item_updated",
        "data": _serialize_playlist_item(item)
    })


async def notify_stream_status(status: str, channel_id: Optional[str] = None):
    """Уведомить клиентов о статусе стрима."""
    message = {"type": "stream_status", "status": status}
    if channel_id:
        await manager.broadcast_to_channel(channel_id, message)
    else:
        await manager.broadcast_all(message)


async def notify_playlist_reordered(channel_id: Optional[str] = None):
    """Уведомить клиентов об изменении порядка плейлиста."""
    message = {"type": "playlist_reordered"}
    if channel_id:
        await manager.broadcast_to_channel(channel_id, message)
    else:
        await manager.broadcast_all(message)
