from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from fastapi import WebSocket


class RoomConnectionManager:
    def __init__(self) -> None:
        self._room_connections: dict[str, dict[int, set[WebSocket]]] = defaultdict(lambda: defaultdict(set))

    async def connect(self, *, room_code: str, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._room_connections[room_code][user_id].add(websocket)

    def disconnect(self, *, room_code: str, user_id: int, websocket: WebSocket) -> None:
        room_users = self._room_connections.get(room_code)
        if not room_users:
            return
        user_connections = room_users.get(user_id)
        if not user_connections:
            return
        user_connections.discard(websocket)
        if not user_connections:
            room_users.pop(user_id, None)
        if not room_users:
            self._room_connections.pop(room_code, None)

    def is_user_connected(self, *, room_code: str, user_id: int) -> bool:
        return bool(self._room_connections.get(room_code, {}).get(user_id))

    def connected_user_ids(self, *, room_code: str) -> set[int]:
        return set(self._room_connections.get(room_code, {}).keys())

    async def send_to_user(self, *, room_code: str, user_id: int, payload: dict) -> None:
        for websocket in list(self._room_connections.get(room_code, {}).get(user_id, set())):
            await websocket.send_json(payload)

    async def broadcast(
        self,
        *,
        room_code: str,
        payload: dict,
        exclude_user_ids: Iterable[int] | None = None,
    ) -> None:
        excluded = set(exclude_user_ids or [])
        room_users = self._room_connections.get(room_code, {})
        for target_user_id, sockets in list(room_users.items()):
            if target_user_id in excluded:
                continue
            for websocket in list(sockets):
                await websocket.send_json(payload)

    async def close_room(self, *, room_code: str, code: int = 4002, reason: str = "Room ended.") -> None:
        room_users = self._room_connections.pop(room_code, {})
        for sockets in room_users.values():
            for websocket in list(sockets):
                await websocket.close(code=code, reason=reason)

    def reset(self) -> None:
        self._room_connections.clear()
