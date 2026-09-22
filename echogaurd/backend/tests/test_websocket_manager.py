import pytest
from unittest.mock import AsyncMock
from fastapi import WebSocket
from app.services.websocket_manager import ConnectionManager

@pytest.mark.anyio
async def test_connect_and_disconnect():
    manager = ConnectionManager()
    ws1 = AsyncMock(spec=WebSocket)
    ws2 = AsyncMock(spec=WebSocket)

    session_id = "session-001"
    user_id = "user-123"

    await manager.connect(ws1, session_id, user_id)
    assert session_id in manager.active_connections
    assert user_id in manager.active_connections[session_id]
    assert ws1 in manager.active_connections[session_id][user_id]

    await manager.connect(ws2, session_id, user_id)
    assert ws2 in manager.active_connections[session_id][user_id]
    assert len(manager.active_connections[session_id][user_id]) == 2

    manager.disconnect(ws1, session_id, user_id)
    assert ws1 not in manager.active_connections[session_id][user_id]
    assert len(manager.active_connections[session_id][user_id]) == 1

    manager.disconnect(ws2, session_id, user_id)
    assert session_id not in manager.active_connections

@pytest.mark.anyio
async def test_broadcast():
    manager = ConnectionManager()
    ws1 = AsyncMock(spec=WebSocket)
    ws2 = AsyncMock(spec=WebSocket)

    session_id = "session-broadcast"
    await manager.connect(ws1, session_id, "user-1")
    await manager.connect(ws2, session_id, "user-2")

    msg = {"type": "ping", "session_id": session_id, "payload": {}}
    await manager.broadcast(session_id, msg)

    ws1.send_json.assert_called_once_with(msg)
    ws2.send_json.assert_called_once_with(msg)

@pytest.mark.anyio
async def test_send_to_user():
    manager = ConnectionManager()
    ws1 = AsyncMock(spec=WebSocket)
    ws2 = AsyncMock(spec=WebSocket)

    session_id = "session-broadcast"
    await manager.connect(ws1, session_id, "user-1")
    await manager.connect(ws2, session_id, "user-2")

    msg = {"type": "ping", "session_id": session_id, "payload": {}}
    await manager.send_to_user(session_id, "user-1", msg)

    ws1.send_json.assert_called_once_with(msg)
    ws2.send_json.assert_not_called()

@pytest.mark.anyio
async def test_send_json_error_handling():
    manager = ConnectionManager()
    ws1 = AsyncMock(spec=WebSocket)
    ws1.send_json.side_effect = Exception("Test error")

    session_id = "session-err"
    await manager.connect(ws1, session_id, "user-1")

    # Should not raise exception
    await manager.send_json(ws1, {"test": 123})
