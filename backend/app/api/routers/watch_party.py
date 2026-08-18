from __future__ import annotations

from fastapi import APIRouter, Depends, Response, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, get_user_from_token
from app.api.deps.db import get_db
from app.db.session import SessionLocal
from app.schemas.watch_party import WatchRoomCreateRequest, WatchRoomDetailResponse
from app.services.watch_party import RoomConnectionManager, WatchRoomService

router = APIRouter(prefix="/watch-party", tags=["watch-party"])
connection_manager = RoomConnectionManager()
service = WatchRoomService(connection_manager=connection_manager, session_factory=SessionLocal)


def _close_code_for_status(status_code: int) -> int:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return 4401
    if status_code == status.HTTP_403_FORBIDDEN:
        return 4403
    if status_code == status.HTTP_404_NOT_FOUND:
        return 4404
    if status_code == status.HTTP_409_CONFLICT:
        return 4409
    return 4400


@router.post("/rooms", response_model=WatchRoomDetailResponse, status_code=status.HTTP_201_CREATED)
def create_watch_room(
    payload: WatchRoomCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchRoomDetailResponse:
    return service.create_room(db=db, user=current_user, payload=payload)


@router.get("/rooms/{room_code}", response_model=WatchRoomDetailResponse, status_code=status.HTTP_200_OK)
def get_watch_room(
    room_code: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchRoomDetailResponse:
    return service.get_room_details(db=db, user=current_user, room_code=room_code)


@router.post("/rooms/{room_code}/join", response_model=WatchRoomDetailResponse, status_code=status.HTTP_200_OK)
def join_watch_room(
    room_code: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchRoomDetailResponse:
    return service.join_room(db=db, user=current_user, room_code=room_code)


@router.post("/rooms/{room_code}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_watch_room(
    room_code: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service.leave_room(db=db, user=current_user, room_code=room_code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/rooms/{room_code}", status_code=status.HTTP_204_NO_CONTENT)
async def end_watch_room(
    room_code: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service.end_room(db=db, user=current_user, room_code=room_code)
    event = service.build_room_ended_event(room_code=room_code, message="The host ended the room.")
    await connection_manager.broadcast(room_code=room_code, payload=event.model_dump(mode="json"))
    await connection_manager.close_room(room_code=room_code, code=4002, reason="Room ended.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.websocket("/ws/{room_code}")
async def watch_party_socket(
    websocket: WebSocket,
    room_code: str,
    db: Session = Depends(get_db),
) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Authentication token is required.")
        return

    try:
        user = get_user_from_token(token, db=db)
        room = service.get_room_for_socket(db=db, user=user, room_code=room_code)
    except Exception as exc:  # noqa: BLE001
        status_code = getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST)
        detail = getattr(exc, "detail", "Could not open the watch room connection.")
        await websocket.close(code=_close_code_for_status(status_code), reason=str(detail))
        return

    await connection_manager.connect(room_code=room_code, user_id=user.id, websocket=websocket)
    if room.host_user_id == user.id:
        service.cancel_host_disconnect(room_code=room_code)

    room = service.get_room_for_socket(db=db, user=user, room_code=room_code)
    participant = service.touch_participant_presence(db=db, room=room, user_id=user.id)

    await websocket.send_json(
        service.build_room_state_event(db=db, room=room, current_user=user).model_dump(mode="json")
    )
    await connection_manager.broadcast(
        room_code=room_code,
        payload=service.build_user_joined_event(participant=participant).model_dump(mode="json"),
        exclude_user_ids=[user.id],
    )

    try:
        while True:
            payload = await websocket.receive_json()
            try:
                room = service.get_room_for_socket(db=db, user=user, room_code=room_code)
                dispatch_mode, event = service.handle_client_event(db=db, room=room, user=user, payload=payload)
            except ValidationError:
                await websocket.send_json(
                    service.build_error_event(
                        code="invalid_payload",
                        message="The room event payload is invalid.",
                    ).model_dump(mode="json")
                )
                continue
            except Exception as exc:  # noqa: BLE001
                await websocket.send_json(
                    service.build_error_event(
                        code="room_event_rejected",
                        message=str(getattr(exc, "detail", "The room event could not be processed.")),
                    ).model_dump(mode="json")
                )
                continue

            if dispatch_mode == "direct":
                await websocket.send_json(event.model_dump(mode="json"))
            else:
                await connection_manager.broadcast(room_code=room_code, payload=event.model_dump(mode="json"))
    except WebSocketDisconnect:
        connection_manager.disconnect(room_code=room_code, user_id=user.id, websocket=websocket)
        try:
            room = service.get_room_details(db=db, user=user, room_code=room_code)
        except Exception:  # noqa: BLE001
            return
        participant = service.participant_repository.get_for_user(
            db=db,
            room_id=room.room.id,
            user_id=user.id,
        )
        if participant is None:
            return
        await connection_manager.broadcast(
            room_code=room_code,
            payload=service.build_user_left_event(participant=participant).model_dump(mode="json"),
            exclude_user_ids=[user.id],
        )
        if user.id == room.room.host_user_id and not connection_manager.is_user_connected(room_code=room_code, user_id=user.id):
            service.schedule_host_disconnect(room_code=room_code)
