import uuid
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.core.config import settings
from app.db.database import get_db
from app.db.repositories.user_repository import UserRepository
from app.services.websocket_manager import manager
from app.models.schemas import WebSocketMessage

router = APIRouter()

async def authenticate_ws(token: str, db: AsyncSession):
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        return None

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    return user

from app.services.signaling_service import SignalingService

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_ws(token, db)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    try:
        await SignalingService.validate_connection(db, session_id, user)
    except ValueError as e:
        await websocket.close(code=1008, reason=str(e))
        return

    await manager.connect(websocket, session_id, str(user.id))

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg_dict = json.loads(data)
                msg = WebSocketMessage(**msg_dict)
            except (json.JSONDecodeError, ValidationError):
                error_msg = {
                    "type": "error",
                    "session_id": session_id,
                    "payload": {
                        "code": "INVALID_FORMAT",
                        "message": "Malformed message or invalid JSON"
                    }
                }
                await manager.send_json(websocket, error_msg)
                continue

            if msg.type == "ping":
                response = {
                    "type": "pong",
                    "session_id": session_id,
                    "payload": {}
                }
                await manager.send_json(websocket, response)
            elif msg.type == "hello":
                response = {
                    "type": "hello_ack",
                    "session_id": session_id,
                    "payload": {"message": "Welcome"}
                }
                await manager.send_json(websocket, response)
            elif msg.type in ["call_offer", "call_answer", "ice_candidate", "call_end"]:
                # Use raw dict for forwarding
                await SignalingService.process_message(db, session_id, user, msg_dict)
            else:
                error_msg = {
                    "type": "error",
                    "session_id": session_id,
                    "payload": {
                        "code": "UNKNOWN_MESSAGE_TYPE",
                        "message": "Unsupported message type"
                    }
                }
                await manager.send_json(websocket, error_msg)
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id, str(user.id))
    except Exception:
        manager.disconnect(websocket, session_id, str(user.id))
