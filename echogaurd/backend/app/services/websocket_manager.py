import logging
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Active WebSocket connections
        #
        # {
        #   session_id: {
        #       user_id: {websocket1, websocket2}
        #   }
        # }
        self.active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}

        # Messages waiting for a participant who has not connected yet.
        #
        # {
        #   session_id: {
        #       user_id: [message1, message2, ...]
        #   }
        # }
        self.pending_messages: Dict[str, Dict[str, list[dict]]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
    ):
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = {}

        if user_id not in self.active_connections[session_id]:
            self.active_connections[session_id][user_id] = set()

        self.active_connections[session_id][user_id].add(websocket)

        logger.info(
            "[WS CONNECT] session=%s user=%s connected_users=%s",
            session_id,
            user_id,
            list(self.active_connections[session_id].keys()),
        )

        # Deliver messages that arrived before this user connected.
        pending = (
            self.pending_messages
            .get(session_id, {})
            .pop(user_id, [])
        )

        if pending:
            logger.info(
                "[WS QUEUE] delivering %d pending messages "
                "to user=%s session=%s",
                len(pending),
                user_id,
                session_id,
            )

        for message in pending:
            await self.send_json(websocket, message)

        # Clean empty queue structures.
        if session_id in self.pending_messages:
            if not self.pending_messages[session_id].get(user_id):
                self.pending_messages[session_id].pop(
                    user_id,
                    None,
                )

            if not self.pending_messages[session_id]:
                self.pending_messages.pop(
                    session_id,
                    None,
                )

    def disconnect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
    ):
        if session_id not in self.active_connections:
            return

        if user_id in self.active_connections[session_id]:
            self.active_connections[session_id][user_id].discard(
                websocket
            )

            if not self.active_connections[session_id][user_id]:
                del self.active_connections[session_id][user_id]

        if not self.active_connections[session_id]:
            del self.active_connections[session_id]

        logger.info(
            "[WS DISCONNECT] session=%s user=%s",
            session_id,
            user_id,
        )

    async def send_json(
        self,
        websocket: WebSocket,
        message: dict,
    ):
        try:
            await websocket.send_json(message)

        except Exception as exc:
            logger.error(
                "Error sending message to websocket: %s",
                exc,
            )

    async def send_to_user(
        self,
        session_id: str,
        user_id: str,
        message: dict,
    ):
        """
        Send a message to a specific participant.

        If the participant is connected, deliver immediately.

        If the participant is not connected yet, temporarily queue
        signaling messages so they can be delivered when they connect.
        """

        connections = (
            self.active_connections
            .get(session_id, {})
            .get(user_id, set())
        )

        if connections:
            logger.info(
                "[WS SEND] session=%s → user=%s type=%s",
                session_id,
                user_id,
                message.get("type"),
            )

            for connection in list(connections):
                await self.send_json(
                    connection,
                    message,
                )

            return

        # Only queue WebRTC signaling messages.
        #
        # We intentionally don't queue call_end because a participant
        # who connects after the call ended should not receive an old
        # call_end event.
        queueable_types = {
            "call_offer",
            "call_answer",
            "ice_candidate",
        }

        message_type = message.get("type")

        if message_type not in queueable_types:
            logger.info(
                "[WS DROP] user=%s is offline and message type=%s "
                "is not queueable",
                user_id,
                message_type,
            )
            return

        if session_id not in self.pending_messages:
            self.pending_messages[session_id] = {}

        if user_id not in self.pending_messages[session_id]:
            self.pending_messages[session_id][user_id] = []

        self.pending_messages[session_id][user_id].append(
            message
        )

        logger.info(
            "[WS QUEUE] session=%s → user=%s type=%s",
            session_id,
            user_id,
            message_type,
        )

    async def broadcast(
        self,
        session_id: str,
        message: dict,
    ):
        if session_id not in self.active_connections:
            return

        for user_id in self.active_connections[session_id]:
            for connection in list(
                self.active_connections[session_id][user_id]
            ):
                await self.send_json(
                    connection,
                    message,
                )


manager = ConnectionManager()