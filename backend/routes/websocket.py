from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from typing import cast

from flask import request

# Make flask_socketio optional for environments where it's not installed
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room  # type: ignore[import]
    FLASK_SOCKETIO_AVAILABLE = True
except ImportError:
    FLASK_SOCKETIO_AVAILABLE = False
    SocketIO = None  # type: ignore
    emit = None  # type: ignore
    join_room = None  # type: ignore
    leave_room = None  # type: ignore

from ..async_bus import list_domain_events
from ..security.auth import decode_access_token
from ..config import load_settings

# Initialize SocketIO only if available
_socketio_class = cast(Any, SocketIO)
socketio: Any = _socketio_class(cors_allowed_origins="*", async_mode="threading") if FLASK_SOCKETIO_AVAILABLE else None

# Track connected clients (Flask-SocketIO)
connected_clients: dict[str, dict[str, Any]] = {}

# FastAPI-compatible async broadcast queue
_broadcast_queue: asyncio.Queue[tuple[str, dict[str, Any]]] | None = None
_fastapi_connected: set[str] = set()


def get_broadcast_queue() -> asyncio.Queue[tuple[str, dict[str, Any]]]:
    """Get or create the broadcast queue for FastAPI WebSocket support."""
    global _broadcast_queue
    if _broadcast_queue is None:
        _broadcast_queue = asyncio.Queue(maxsize=1000)
    return _broadcast_queue


def init_websocket(app: Any) -> None:
    """Initialize WebSocket with Flask app."""
    if FLASK_SOCKETIO_AVAILABLE and socketio:
        socketio.init_app(app)


# Define WebSocket handlers only if flask_socketio is available
if FLASK_SOCKETIO_AVAILABLE and socketio is not None:
    _socketio = cast(Any, socketio)
    _emit = cast(Any, emit)
    _join_room = cast(Any, join_room)
    _leave_room = cast(Any, leave_room)

    @_socketio.on("connect")
    def handle_connect() -> None:
        """Handle client connection."""
        client_id = request.sid  # type: ignore[attr-defined]
        token = request.args.get("token")
        
        # Validate token if provided
        user_info = {"role": "anonymous", "username": "anonymous"}
        if token:
            try:
                settings = load_settings()
                user = decode_access_token(token, settings)
                user_info = {"role": user.role, "username": user.username}
            except Exception:
                pass
        
        connected_clients[client_id] = {
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "user": user_info,
            "subscriptions": set(),
        }
        
        _emit("connected", {
            "client_id": client_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user_info,
        })
        
        print(f"[WebSocket] Client connected: {client_id} (user: {user_info['username']})")


    @_socketio.on("disconnect")
    def handle_disconnect() -> None:
        """Handle client disconnection."""
        client_id = request.sid  # type: ignore[attr-defined]
        if client_id in connected_clients:
            del connected_clients[client_id]
        
        print(f"[WebSocket] Client disconnected: {client_id}")


    @_socketio.on("subscribe")
    def handle_subscribe(data: dict[str, Any]) -> None:
        """Handle channel subscription."""
        client_id = request.sid  # type: ignore[attr-defined]
        channels = data.get("channels", [])
        
        if client_id in connected_clients:
            for channel in channels:
                _join_room(channel)
                connected_clients[client_id]["subscriptions"].add(channel)

        _emit("subscribed", {
            "channels": channels,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


    @_socketio.on("unsubscribe")
    def handle_unsubscribe(data: dict[str, Any]) -> None:
        """Handle channel unsubscription."""
        client_id = request.sid  # type: ignore[attr-defined]
        channels = data.get("channels", [])
        
        if client_id in connected_clients:
            for channel in channels:
                _leave_room(channel)
                connected_clients[client_id]["subscriptions"].discard(channel)

        _emit("unsubscribed", {
            "channels": channels,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


    @_socketio.on("ping")
    def handle_ping() -> None:
        """Handle ping message."""
        _emit("pong", {"timestamp": datetime.now(timezone.utc).isoformat()})


def broadcast_notification(
    event_type: str,
    payload: dict[str, Any],
    channel: str = "notifications",
) -> None:
    """Broadcast notification to all subscribed clients."""
    message = {
        "id": f"msg-{datetime.now(timezone.utc).timestamp()}",
        "event_type": event_type,
        "service": "notification-service",
        "payload": payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Emit via Flask-SocketIO if initialized
    if socketio is not None:
        try:
            socketio.emit("notification", message, room=channel)
        except RuntimeError:
            pass

    # Also queue for FastAPI WebSocket
    try:
        queue = get_broadcast_queue()
        queue.put_nowait(("notification", {"message": message, "room": channel}))
    except asyncio.QueueFull:
        pass


def broadcast_event(
    event_type: str,
    data: dict[str, Any],
    channel: str = "events",
) -> None:
    """Broadcast domain event to all subscribed clients."""
    message = {
        "id": f"evt-{datetime.now(timezone.utc).timestamp()}",
        "event_type": event_type,
        "service": "event-bus",
        "payload": data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Emit via Flask-SocketIO if initialized
    if socketio is not None:
        try:
            socketio.emit("event", message, room=channel)
        except RuntimeError:
            pass

    # Also queue for FastAPI WebSocket
    try:
        queue = get_broadcast_queue()
        queue.put_nowait(("event", {"message": message, "room": channel}))
    except asyncio.QueueFull:
        pass


def broadcast_proposal_update(
    proposal_id: str,
    status: str,
    action: str,
    actor: str,
) -> None:
    """Broadcast proposal state change."""
    message = {
        "id": f"prop-{datetime.now(timezone.utc).timestamp()}",
        "event_type": "ProposalStateChanged",
        "service": "proposal-service",
        "payload": {
            "proposal_id": proposal_id,
            "status": status,
            "action": action,
            "actor": actor,
        },
        "correlation_id": proposal_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Emit via Flask-SocketIO if initialized
    if socketio is not None:
        try:
            socketio.emit("proposal_update", message, room="proposals")
        except RuntimeError:
            pass

    # Also queue for FastAPI WebSocket
    try:
        queue = get_broadcast_queue()
        queue.put_nowait(("proposal_update", {"message": message, "room": "proposals"}))
    except asyncio.QueueFull:
        pass


def get_connected_clients_count() -> int:
    """Get number of connected clients."""
    return len(connected_clients)


def get_channel_subscribers(channel: str) -> list[str]:
    """Get list of clients subscribed to a channel."""
    subscribers = []
    for client_id, info in connected_clients.items():
        if channel in info.get("subscriptions", set()):
            subscribers.append(client_id)
    return subscribers
