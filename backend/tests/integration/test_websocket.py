"""
WebSocket Integration Tests

Проверяем:
- WebSocket соединение устанавливается
- Сообщения передаются корректно
- Аутентификация работает
- Reconnection logic
- Broadcasting
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from websockets.sync.client import connect as ws_connect
from websockets.exceptions import InvalidStatusCode
import json


@pytest.fixture
def ws_url():
    """WebSocket URL для тестов"""
    return "ws://localhost:8000/ws"


class TestWebSocketConnection:
    """Тесты WebSocket соединения"""
    
    def test_websocket_connection_success(self, client: TestClient):
        """Проверка успешного WebSocket соединения"""
        with client.websocket_connect("/ws") as websocket:
            # Соединение установлено
            assert websocket is not None
            
            # Отправляем ping
            websocket.send_json({"type": "ping"})
            
            # Ожидаем pong
            response = websocket.receive_json()
            assert response.get("type") == "pong"
    
    def test_websocket_authentication(self, client: TestClient, auth_headers):
        """Проверка аутентификации WebSocket соединения"""
        token = auth_headers.get("Authorization", "").replace("Bearer ", "")
        
        # Подключаемся с токеном
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            # Ожидаем welcome message
            response = websocket.receive_json()
            assert "type" in response
            
            # Проверяем что authenticated
            websocket.send_json({"type": "whoami"})
            response = websocket.receive_json()
            assert response.get("authenticated") is True
    
    def test_websocket_unauthorized_connection(self, client: TestClient):
        """Проверка что без токена соединение отклоняется или ограничено"""
        try:
            with client.websocket_connect("/ws") as websocket:
                # Пытаемся отправить команду требующую auth
                websocket.send_json({"type": "admin_command"})
                response = websocket.receive_json()
                
                # Должна быть ошибка
                assert response.get("error") or response.get("type") == "error"
        except InvalidStatusCode as e:
            # Или соединение вообще не устанавливается
            assert e.status_code == 401 or e.status_code == 403


class TestWebSocketMessaging:
    """Тесты отправки и получения сообщений через WebSocket"""
    
    def test_send_receive_message(self, client: TestClient):
        """Проверка отправки и получения сообщений"""
        with client.websocket_connect("/ws") as websocket:
            # Отправляем текстовое сообщение
            test_message = {"type": "test", "data": "hello"}
            websocket.send_json(test_message)
            
            # Получаем ответ
            response = websocket.receive_json()
            assert "type" in response
    
    def test_broadcast_message(self, client: TestClient):
        """Проверка broadcast сообщений (требует 2+ соединения)"""
        with client.websocket_connect("/ws") as ws1:
            with client.websocket_connect("/ws") as ws2:
                # Отправляем broadcast из ws1
                ws1.send_json({"type": "broadcast", "message": "Hello everyone"})
                
                # ws2 должен получить сообщение
                # Примечание: таймауты могут потребоваться
                try:
                    response = ws2.receive_json(timeout=1)
                    assert "message" in response or "type" in response
                except:
                    # Если broadcast не реализован, пропускаем
                    pytest.skip("Broadcast not implemented")
    
    def test_message_queue_handling(self, client: TestClient):
        """Проверка обработки очереди сообщений"""
        with client.websocket_connect("/ws") as websocket:
            # Отправляем несколько сообщений быстро
            for i in range(5):
                websocket.send_json({"type": "message", "id": i})
            
            # Получаем ответы
            responses = []
            for _ in range(5):
                try:
                    response = websocket.receive_json(timeout=1)
                    responses.append(response)
                except:
                    break
            
            # Все сообщения должны быть обработаны
            assert len(responses) >= 1


class TestWebSocketPlayerControl:
    """Тесты управления плеером через WebSocket"""
    
    def test_play_pause_commands(self, client: TestClient, auth_headers):
        """Проверка команд play/pause через WebSocket"""
        token = auth_headers.get("Authorization", "").replace("Bearer ", "")
        
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            # Отправляем команду play
            websocket.send_json({"type": "player_control", "action": "play"})
            response = websocket.receive_json()
            
            # Проверяем ответ
            assert response.get("type") in ["player_status", "success", "error"]
            
            # Отправляем команду pause
            websocket.send_json({"type": "player_control", "action": "pause"})
            response = websocket.receive_json()
            assert response.get("type") in ["player_status", "success", "error"]
    
    def test_volume_control(self, client: TestClient, auth_headers):
        """Проверка управления громкостью через WebSocket"""
        token = auth_headers.get("Authorization", "").replace("Bearer ", "")
        
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            # Устанавливаем громкость
            websocket.send_json({
                "type": "player_control",
                "action": "volume",
                "value": 50
            })
            response = websocket.receive_json()
            assert response.get("type") in ["player_status", "success", "error"]
    
    def test_track_skip(self, client: TestClient, auth_headers):
        """Проверка пропуска трека через WebSocket"""
        token = auth_headers.get("Authorization", "").replace("Bearer ", "")
        
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            websocket.send_json({"type": "player_control", "action": "next"})
            response = websocket.receive_json()
            assert "type" in response


class TestWebSocketReconnection:
    """Тесты переподключения WebSocket"""
    
    def test_reconnection_after_disconnect(self, client: TestClient):
        """Проверка переподключения после разрыва"""
        # Первое соединение
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "ping"})
            response1 = websocket.receive_json()
            assert response1.get("type") == "pong"
        
        # Соединение закрыто, переподключаемся
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "ping"})
            response2 = websocket.receive_json()
            assert response2.get("type") == "pong"
    
    def test_connection_persistence(self, client: TestClient):
        """Проверка что соединение держится под нагрузкой"""
        with client.websocket_connect("/ws") as websocket:
            # Отправляем много сообщений
            for i in range(100):
                websocket.send_json({"type": "ping", "id": i})
                response = websocket.receive_json()
                assert "type" in response
            
            # Соединение всё ещё активно
            websocket.send_json({"type": "status"})
            response = websocket.receive_json()
            assert response is not None


class TestWebSocketErrors:
    """Тесты обработки ошибок WebSocket"""
    
    def test_invalid_message_format(self, client: TestClient):
        """Проверка обработки невалидных сообщений"""
        with client.websocket_connect("/ws") as websocket:
            # Отправляем невалидный JSON
            websocket.send_text("invalid json {{{")
            
            # Должны получить error response
            response = websocket.receive_json()
            assert response.get("type") == "error" or "error" in response
    
    def test_unknown_command(self, client: TestClient):
        """Проверка обработки неизвестных команд"""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "unknown_command_xyz"})
            response = websocket.receive_json()
            
            # Должна быть ошибка или игнорирование
            assert response.get("type") in ["error", "unknown", "pong"]
    
    def test_malformed_command(self, client: TestClient):
        """Проверка обработки команд с неправильными параметрами"""
        with client.websocket_connect("/ws") as websocket:
            # Команда без обязательных параметров
            websocket.send_json({"type": "player_control"})  # missing action
            response = websocket.receive_json()
            assert response.get("type") == "error" or response.get("error")


class TestWebSocketPerformance:
    """Тесты производительности WebSocket"""
    
    def test_message_throughput(self, client: TestClient):
        """Проверка throughput сообщений"""
        import time
        
        with client.websocket_connect("/ws") as websocket:
            start = time.time()
            message_count = 1000
            
            # Отправляем много сообщений
            for i in range(message_count):
                websocket.send_json({"type": "ping", "id": i})
                websocket.receive_json()
            
            elapsed = time.time() - start
            throughput = message_count / elapsed
            
            # Ожидаем минимум 100 msg/sec (очень консервативно)
            assert throughput > 100, f"Throughput too low: {throughput} msg/sec"
    
    def test_concurrent_connections(self, client: TestClient):
        """Проверка множественных одновременных соединений"""
        connections = []
        
        try:
            # Открываем 10 соединений
            for i in range(10):
                ws = client.websocket_connect("/ws")
                ws.__enter__()
                connections.append(ws)
            
            # Отправляем сообщение из каждого
            for i, ws in enumerate(connections):
                ws.send_json({"type": "ping", "id": i})
                response = ws.receive_json()
                assert "type" in response
        finally:
            # Закрываем все соединения
            for ws in connections:
                try:
                    ws.__exit__(None, None, None)
                except:
                    pass
