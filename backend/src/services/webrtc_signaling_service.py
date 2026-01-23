"""
WebRTC Signaling Service для guest co-hosting.

Сервис управляет WebRTC сигналингом между хостом и гостями для совместного ведения трансляции.
Обрабатывает SDP offer/answer и ICE candidates для установления P2P соединений.

Features:
- Управление WebRTC соединениями для guest co-hosting
- Обработка SDP offer/answer и ICE candidates
- Отслеживание качества соединения
- Интеграция с GuestSession моделью
- Поддержка разрешений (permissions) для гостей
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Set, TYPE_CHECKING
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from src.models.guest_session import GuestSession
    from src.models.live_stream import LiveStream

logger = logging.getLogger("webrtc_signaling")


class WebRTCSignalingService:
    """
    Сервис для управления WebRTC сигналингом между хостом и гостями.

    Обеспечивает:
    - Регистрацию WebRTC соединений
    - Передачу SDP offer/answer между пирами
    - Обмен ICE candidates
    - Отслеживание качества соединения
    - Управление жизненным циклом guest sessions
    """

    def __init__(self, db_session: Session):
        """
        Инициализировать WebRTC signaling service.

        Args:
            db_session: SQLAlchemy сессия для работы с БД
        """
        self.db = db_session
        self.logger = logger

        # live_stream_id -> user_id -> connection_id
        self._active_connections: Dict[str, Dict[str, str]] = {}

        # connection_id -> WebSocket (mock, actual WS managed in websocket.py)
        self._connection_websockets: Dict[str, object] = {}

        # connection_id -> connection quality metrics
        self._connection_quality: Dict[str, dict] = {}

        self._lock = asyncio.Lock()

    async def register_connection(
        self,
        live_stream_id: str,
        user_id: int,
        role: str = "guest"
    ) -> str:
        """
        Зарегистрировать новое WebRTC соединение.

        Args:
            live_stream_id: ID live stream
            user_id: ID пользователя (хоста или гостя)
            role: Роль ("host" или "guest")

        Returns:
            connection_id: Уникальный ID соединения
        """
        async with self._lock:
            # Генерируем уникальный ID соединения
            connection_id = str(uuid.uuid4())

            # Регистрируем соединение
            if live_stream_id not in self._active_connections:
                self._active_connections[live_stream_id] = {}

            self._active_connections[live_stream_id][str(user_id)] = connection_id
            self._connection_websockets[connection_id] = None  # Will be set by WebSocket handler
            self._connection_quality[connection_id] = {
                "bitrate": 0,
                "packet_loss": 0.0,
                "rtt": 0,
                "last_update": datetime.now(timezone.utc).isoformat()
            }

            self.logger.info(
                f"Registered WebRTC connection: stream={live_stream_id}, "
                f"user={user_id}, role={role}, conn_id={connection_id}"
            )

            # Обновляем GuestSession если это гость
            if role == "guest":
                await self._update_guest_session_connection(
                    live_stream_id=live_stream_id,
                    user_id=user_id,
                    connection_id=connection_id
                )

            return connection_id

    async def unregister_connection(
        self,
        connection_id: str,
        live_stream_id: str,
        user_id: int,
        role: str = "guest"
    ):
        """
        Отрегистрировать WebRTC соединение.

        Args:
            connection_id: ID соединения
            live_stream_id: ID live stream
            user_id: ID пользователя
            role: Роль ("host" или "guest")
        """
        async with self._lock:
            # Удаляем из активных соединений
            if live_stream_id in self._active_connections:
                self._active_connections[live_stream_id].pop(str(user_id), None)

                # Удаляем stream если нет соединений
                if not self._active_connections[live_stream_id]:
                    self._active_connections.pop(live_stream_id)

            # Удаляем websocket
            self._connection_websockets.pop(connection_id, None)

            # Удаляем метрики качества
            self._connection_quality.pop(connection_id, None)

            self.logger.info(
                f"Unregistered WebRTC connection: conn_id={connection_id}, "
                f"stream={live_stream_id}, user={user_id}"
            )

            # Обновляем GuestSession если это гость
            if role == "guest":
                await self._update_guest_session_left(
                    live_stream_id=live_stream_id,
                    user_id=user_id
                )

    async def handle_offer(
        self,
        live_stream_id: str,
        from_user_id: int,
        to_user_id: int,
        offer_sdp: dict
    ) -> dict:
        """
        Обработать SDP offer от одного пира к другому.

        Args:
            live_stream_id: ID live stream
            from_user_id: ID отправителя
            to_user_id: ID получателя
            offer_sdp: SDP offer объект

        Returns:
            Сообщение для передачи целевому пиру
        """
        connection_id = await self._get_connection_id(live_stream_id, from_user_id)

        if not connection_id:
            raise ValueError(f"Connection not found for user {from_user_id} in stream {live_stream_id}")

        message = {
            "type": "offer",
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "connection_id": connection_id,
            "sdp": offer_sdp,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.logger.debug(f"Created offer message: from={from_user_id} to={to_user_id}")

        return message

    async def handle_answer(
        self,
        live_stream_id: str,
        from_user_id: int,
        to_user_id: int,
        answer_sdp: dict
    ) -> dict:
        """
        Обработать SDP answer от одного пира к другому.

        Args:
            live_stream_id: ID live stream
            from_user_id: ID отправителя
            to_user_id: ID получателя
            answer_sdp: SDP answer объект

        Returns:
            Сообщение для передачи целевому пиру
        """
        connection_id = await self._get_connection_id(live_stream_id, from_user_id)

        if not connection_id:
            raise ValueError(f"Connection not found for user {from_user_id} in stream {live_stream_id}")

        message = {
            "type": "answer",
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "connection_id": connection_id,
            "sdp": answer_sdp,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.logger.debug(f"Created answer message: from={from_user_id} to={to_user_id}")

        return message

    async def handle_ice_candidate(
        self,
        live_stream_id: str,
        from_user_id: int,
        to_user_id: int,
        candidate: dict
    ) -> dict:
        """
        Обработать ICE candidate от одного пира к другому.

        Args:
            live_stream_id: ID live stream
            from_user_id: ID отправителя
            to_user_id: ID получателя
            candidate: ICE candidate объект

        Returns:
            Сообщение для передачи целевому пиру
        """
        connection_id = await self._get_connection_id(live_stream_id, from_user_id)

        if not connection_id:
            raise ValueError(f"Connection not found for user {from_user_id} in stream {live_stream_id}")

        message = {
            "type": "ice_candidate",
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "connection_id": connection_id,
            "candidate": candidate,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.logger.debug(f"Created ICE candidate message: from={from_user_id} to={to_user_id}")

        return message

    async def update_connection_quality(
        self,
        connection_id: str,
        bitrate: int,
        packet_loss: float,
        rtt: int
    ):
        """
        Обновить метрики качества соединения.

        Args:
            connection_id: ID соединения
            bitrate: Текущий битрейт (bps)
            packet_loss: Потеря пакетов (0.0-1.0)
            rtt: Round-trip time (ms)
        """
        async with self._lock:
            if connection_id in self._connection_quality:
                self._connection_quality[connection_id] = {
                    "bitrate": bitrate,
                    "packet_loss": packet_loss,
                    "rtt": rtt,
                    "last_update": datetime.now(timezone.utc).isoformat()
                }

                self.logger.debug(
                    f"Updated connection quality: conn_id={connection_id}, "
                    f"bitrate={bitrate}, packet_loss={packet_loss}, rtt={rtt}"
                )

                # Обновляем в GuestSession
                await self._update_guest_session_quality(connection_id, packet_loss, rtt)

    async def get_connection_quality(self, connection_id: str) -> Optional[dict]:
        """
        Получить метрики качества соединения.

        Args:
            connection_id: ID соединения

        Returns:
            Словарь с метриками или None
        """
        async with self._lock:
            return self._connection_quality.get(connection_id)

    async def get_active_connections(
        self,
        live_stream_id: str
    ) -> Dict[str, str]:
        """
        Получить активные соединения для live stream.

        Args:
            live_stream_id: ID live stream

        Returns:
            Словарь {user_id: connection_id}
        """
        async with self._lock:
            return self._active_connections.get(live_stream_id, {}).copy()

    async def get_connection_id_for_user(
        self,
        live_stream_id: str,
        user_id: int
    ) -> Optional[str]:
        """
        Получить ID соединения для пользователя.

        Args:
            live_stream_id: ID live stream
            user_id: ID пользователя

        Returns:
            connection_id или None
        """
        return await self._get_connection_id(live_stream_id, user_id)

    async def is_user_connected(
        self,
        live_stream_id: str,
        user_id: int
    ) -> bool:
        """
        Проверить, подключен ли пользователь к live stream.

        Args:
            live_stream_id: ID live stream
            user_id: ID пользователя

        Returns:
            True если подключен
        """
        async with self._lock:
            return (
                live_stream_id in self._active_connections and
                str(user_id) in self._active_connections[live_stream_id]
            )

    async def disconnect_all_from_stream(self, live_stream_id: str):
        """
        Отключить всех участников от live stream.

        Args:
            live_stream_id: ID live stream
        """
        async with self._lock:
            if live_stream_id in self._active_connections:
                connections = self._active_connections[live_stream_id].copy()

                for user_id_str, connection_id in connections.items():
                    # Удаляем соединение
                    self._connection_websockets.pop(connection_id, None)
                    self._connection_quality.pop(connection_id, None)

                # Очищаем stream
                del self._active_connections[live_stream_id]

                self.logger.info(f"Disconnected all from stream {live_stream_id}")

    async def get_stream_stats(self, live_stream_id: str) -> dict:
        """
        Получить статистику соединений для live stream.

        Args:
            live_stream_id: ID live stream

        Returns:
            Словарь со статистикой
        """
        async with self._lock:
            connections = self._active_connections.get(live_stream_id, {})
            connection_ids = list(connections.values())

            # Собираем метрики качества
            qualities = [
                self._connection_quality.get(conn_id, {})
                for conn_id in connection_ids
                if conn_id in self._connection_quality
            ]

            avg_bitrate = sum(q.get("bitrate", 0) for q in qualities) // len(qualities) if qualities else 0
            avg_packet_loss = sum(q.get("packet_loss", 0.0) for q in qualities) / len(qualities) if qualities else 0.0
            avg_rtt = sum(q.get("rtt", 0) for q in qualities) // len(qualities) if qualities else 0

            return {
                "live_stream_id": live_stream_id,
                "active_connections": len(connections),
                "average_bitrate": avg_bitrate,
                "average_packet_loss": avg_packet_loss,
                "average_rtt": avg_rtt,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # === Private helper methods ===

    async def _get_connection_id(
        self,
        live_stream_id: str,
        user_id: int
    ) -> Optional[str]:
        """Получить connection_id для пользователя в stream."""
        async with self._lock:
            stream_connections = self._active_connections.get(live_stream_id, {})
            return stream_connections.get(str(user_id))

    async def _update_guest_session_connection(
        self,
        live_stream_id: str,
        user_id: int,
        connection_id: str
    ):
        """Обновить GuestSession с connection_id."""
        try:
            from src.models.guest_session import GuestSession, GuestSessionStatus

            guest_session = self.db.query(GuestSession).filter(
                GuestSession.live_stream_id == live_stream_id,
                GuestSession.user_id == user_id,
                GuestSession.status.in_([
                    GuestSessionStatus.PENDING,
                    GuestSessionStatus.ACCEPTED,
                    GuestSessionStatus.ACTIVE
                ])
            ).first()

            if guest_session:
                guest_session.webrtc_connection_id = connection_id
                guest_session.update_last_active()
                self.db.commit()

                self.logger.debug(
                    f"Updated GuestSession {guest_session.id} with connection_id={connection_id}"
                )
        except Exception as e:
            self.logger.error(f"Failed to update GuestSession connection: {e}")

    async def _update_guest_session_quality(
        self,
        connection_id: str,
        packet_loss: float,
        rtt: int
    ):
        """Обновить качество соединения в GuestSession."""
        try:
            from src.models.guest_session import GuestSession

            guest_session = self.db.query(GuestSession).filter(
                GuestSession.webrtc_connection_id == connection_id
            ).first()

            if guest_session:
                # Определяем качество на основе packet loss и RTT
                if packet_loss < 0.01 and rtt < 100:
                    quality = "excellent"
                elif packet_loss < 0.05 and rtt < 200:
                    quality = "good"
                elif packet_loss < 0.10 and rtt < 500:
                    quality = "fair"
                else:
                    quality = "poor"

                guest_session.connection_quality = quality
                guest_session.update_last_active()
                self.db.commit()

                self.logger.debug(
                    f"Updated GuestSession {guest_session.id} quality={quality}"
                )
        except Exception as e:
            self.logger.error(f"Failed to update GuestSession quality: {e}")

    async def _update_guest_session_left(
        self,
        live_stream_id: str,
        user_id: int
    ):
        """Обновить GuestSession когда гость отключается."""
        try:
            from src.models.guest_session import GuestSession, GuestSessionStatus

            guest_session = self.db.query(GuestSession).filter(
                GuestSession.live_stream_id == live_stream_id,
                GuestSession.user_id == user_id,
                GuestSession.status == GuestSessionStatus.ACTIVE
            ).first()

            if guest_session:
                guest_session.mark_as_left("Connection closed")
                self.db.commit()

                self.logger.info(f"Marked GuestSession {guest_session.id} as left")
        except Exception as e:
            self.logger.error(f"Failed to update GuestSession left: {e}")
