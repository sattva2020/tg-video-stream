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


# === Queue Events (US1 - Queue System) ===

async def notify_queue_update(
    channel_id: int,
    operation: str,
    item_id: Optional[str] = None,
    position: Optional[int] = None,
    item_data: Optional[dict] = None
):
    """
    Уведомить клиентов об изменении очереди.
    
    Args:
        channel_id: ID канала
        operation: Тип операции (add, remove, move, clear, skip, priority_add)
        item_id: ID элемента (опционально)
        position: Новая позиция (для move)
        item_data: Данные элемента (для add)
    """
    message = {
        "type": "queue_update",
        "channel_id": channel_id,
        "operation": operation,
        "timestamp": _get_timestamp()
    }
    
    if item_id:
        message["item_id"] = item_id
    if position is not None:
        message["position"] = position
    if item_data:
        message["item"] = item_data
    
    await manager.broadcast_to_channel(str(channel_id), message)
    
    # Также отправляем в общий канал
    await manager.broadcast_to_channel(None, message)


async def notify_stream_state_update(
    channel_id: int,
    status: str,
    current_item_id: Optional[str] = None,
    listeners_count: int = 0,
    is_placeholder: bool = False,
    current_position: int = 0
):
    """
    Уведомить клиентов об изменении состояния стрима.
    
    Args:
        channel_id: ID канала
        status: Статус (playing, paused, stopped, placeholder)
        current_item_id: ID текущего трека
        listeners_count: Количество слушателей
        is_placeholder: Воспроизводится ли placeholder
        current_position: Текущая позиция в секундах
    """
    message = {
        "type": "stream_state",
        "channel_id": channel_id,
        "status": status,
        "current_item_id": current_item_id,
        "listeners_count": listeners_count,
        "is_placeholder": is_placeholder,
        "current_position": current_position,
        "timestamp": _get_timestamp()
    }
    
    await manager.broadcast_to_channel(str(channel_id), message)
    await manager.broadcast_to_channel(None, message)


async def notify_auto_end_warning(
    channel_id: int,
    remaining_seconds: int,
    timeout_at: str
):
    """
    Уведомить клиентов о скором auto-end.
    
    Args:
        channel_id: ID канала
        remaining_seconds: Оставшееся время до auto-end
        timeout_at: ISO timestamp завершения
    """
    message = {
        "type": "auto_end_warning",
        "channel_id": channel_id,
        "remaining_seconds": remaining_seconds,
        "timeout_at": timeout_at,
        "timestamp": _get_timestamp()
    }
    
    await manager.broadcast_to_channel(str(channel_id), message)
    await manager.broadcast_to_channel(None, message)


async def notify_auto_end_cancelled(channel_id: int):
    """Уведомить об отмене auto-end таймера."""
    message = {
        "type": "auto_end_cancelled",
        "channel_id": channel_id,
        "timestamp": _get_timestamp()
    }
    
    await manager.broadcast_to_channel(str(channel_id), message)
    await manager.broadcast_to_channel(None, message)


async def notify_auto_end_triggered(channel_id: int, reason: str):
    """
    Уведомить о срабатывании auto-end.
    
    Args:
        channel_id: ID канала
        reason: Причина (timeout, no_listeners, manual)
    """
    message = {
        "type": "auto_end_triggered",
        "channel_id": channel_id,
        "reason": reason,
        "timestamp": _get_timestamp()
    }
    
    await manager.broadcast_to_channel(str(channel_id), message)
    await manager.broadcast_to_channel(None, message)


# === Helper functions ===

def _get_timestamp() -> str:
    """Получить текущий timestamp в ISO формате."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# === Metrics Broadcast (T047 - Periodic metrics update) ===

_metrics_broadcast_task: Optional[asyncio.Task] = None


async def _periodic_metrics_broadcast():
    """
    Периодическая рассылка метрик всем подключенным клиентам.
    
    Интервал: 5 секунд
    """
    while True:
        try:
            await asyncio.sleep(5)
            
            # Собираем метрики
            metrics = await _get_current_metrics()
            
            # Отправляем всем
            await manager.broadcast_all({
                "type": "metrics_update",
                "data": metrics,
                "timestamp": _get_timestamp()
            })
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error(f"Metrics broadcast error: {e}")
            await asyncio.sleep(5)


async def _get_current_metrics() -> dict:
    """
    Получить текущие метрики системы.
    
    Returns:
        Dict с метриками стримов, очередей и системы
    """
    try:
        from src.services.prometheus_metrics import prometheus_helper
        
        stats = prometheus_helper.get_current_values()
        
        return {
            "streams": {
                "active": stats.get("streams", {}).get("active", 0),
                "total_listeners": stats.get("streams", {}).get("listeners", 0)
            },
            "queue": {
                "total_items": stats.get("queue", {}).get("size", 0)
            },
            "http": {
                "requests_in_progress": stats.get("http", {}).get("in_progress", 0)
            },
            "websocket": {
                "connections": manager._total_connections()
            }
        }
    except Exception as e:
        log.error(f"Failed to get metrics: {e}")
        return {}


def start_metrics_broadcast():
    """Запустить фоновую задачу рассылки метрик."""
    global _metrics_broadcast_task
    
    if _metrics_broadcast_task is None or _metrics_broadcast_task.done():
        _metrics_broadcast_task = asyncio.create_task(_periodic_metrics_broadcast())
        log.info("Started periodic metrics broadcast")


def stop_metrics_broadcast():
    """Остановить фоновую задачу рассылки метрик."""
    global _metrics_broadcast_task
    
    if _metrics_broadcast_task and not _metrics_broadcast_task.done():
        _metrics_broadcast_task.cancel()
        log.info("Stopped periodic metrics broadcast")


async def notify_listeners_update(channel_id: int, listeners_count: int):
    """
    Уведомить об изменении количества слушателей.
    
    Args:
        channel_id: ID канала
        listeners_count: Текущее количество слушателей
    """
    message = {
        "type": "listeners_update",
        "channel_id": channel_id,
        "listeners_count": listeners_count,
        "timestamp": _get_timestamp()
    }
    
    await manager.broadcast_to_channel(str(channel_id), message)
    await manager.broadcast_to_channel(None, message)


# Экспорт connection_manager для использования в других модулях
connection_manager = manager
