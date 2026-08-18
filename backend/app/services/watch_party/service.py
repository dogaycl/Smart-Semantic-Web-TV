from __future__ import annotations

import asyncio
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.user import User
from app.models.watch_room import WatchRoom
from app.models.watch_room_message import WatchRoomMessage
from app.models.watch_room_participant import WatchRoomParticipant
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.watch_room_repository import (
    WatchRoomMessageRepository,
    WatchRoomParticipantRepository,
    WatchRoomRepository,
)
from app.schemas.watch_party import (
    RoomPlaybackState,
    WatchPartyChatBroadcastEvent,
    WatchPartyChatMessageEvent,
    WatchPartyContentChangeEvent,
    WatchPartyErrorEvent,
    WatchPartyPauseEvent,
    WatchPartyPlayEvent,
    WatchPartyPlaybackEvent,
    WatchPartyRoomEndedEvent,
    WatchPartyRoomStateEvent,
    WatchPartySeekEvent,
    WatchPartySyncRequestEvent,
    WatchPartySyncStateEvent,
    WatchPartyUserEvent,
    WatchRoomCreateRequest,
    WatchRoomDetailResponse,
    WatchRoomMessageRead,
    WatchRoomParticipantRead,
    WatchRoomRead,
    WatchRoomTargetRead,
    watch_party_client_event_adapter,
)
from app.services.live_tv.service import LiveTVService
from app.services.playback.service import CatalogPlaybackService
from app.services.watch_party.manager import RoomConnectionManager


@dataclass(slots=True)
class ResolvedTarget:
    target: WatchRoomTargetRead
    playback_supported: bool
    supports_seek: bool
    default_playback_state: RoomPlaybackState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class ChatService:
    def __init__(self, *, message_repository: WatchRoomMessageRepository | None = None) -> None:
        self.message_repository = message_repository or WatchRoomMessageRepository()

    def create_message(
        self,
        *,
        db: Session,
        room: WatchRoom,
        user: User,
        message_text: str,
    ) -> WatchRoomMessage:
        settings = get_settings()
        normalized = " ".join(message_text.split()).strip()
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty.")
        if len(normalized) > settings.watch_party_chat_message_max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Message must be at most {settings.watch_party_chat_message_max_length} characters.",
            )

        message = self.message_repository.create(
            room_id=room.id,
            user_id=user.id,
            message_text=normalized,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message


class WatchRoomService:
    def __init__(
        self,
        *,
        room_repository: WatchRoomRepository | None = None,
        participant_repository: WatchRoomParticipantRepository | None = None,
        message_repository: WatchRoomMessageRepository | None = None,
        catalog_repository: CatalogRepository | None = None,
        channel_repository: ChannelRepository | None = None,
        playback_service: CatalogPlaybackService | None = None,
        live_tv_service: LiveTVService | None = None,
        chat_service: ChatService | None = None,
        connection_manager: RoomConnectionManager | None = None,
        session_factory: sessionmaker | None = None,
    ) -> None:
        self.room_repository = room_repository or WatchRoomRepository()
        self.participant_repository = participant_repository or WatchRoomParticipantRepository()
        self.message_repository = message_repository or WatchRoomMessageRepository()
        self.catalog_repository = catalog_repository or CatalogRepository()
        self.channel_repository = channel_repository or ChannelRepository()
        self.playback_service = playback_service or CatalogPlaybackService(catalog_repository=self.catalog_repository)
        self.live_tv_service = live_tv_service or LiveTVService()
        self.chat_service = chat_service or ChatService(message_repository=self.message_repository)
        self.connection_manager = connection_manager or RoomConnectionManager()
        self.session_factory = session_factory
        self._host_disconnect_tasks: dict[str, asyncio.Task] = {}

    def reset_runtime_state(self) -> None:
        for task in self._host_disconnect_tasks.values():
            task.cancel()
        self._host_disconnect_tasks.clear()
        self.connection_manager.reset()

    def create_room(self, *, db: Session, user: User, payload: WatchRoomCreateRequest) -> WatchRoomDetailResponse:
        resolved = self._resolve_target(
            db=db,
            target_type=payload.target_type,
            content_slug=payload.content_slug,
            channel_id=payload.channel_id,
        )
        room = self.room_repository.create(
            room_code=self._generate_room_code(db=db),
            host_user_id=user.id,
            target_type=payload.target_type,
            content_slug=payload.content_slug if payload.target_type == "catalog" else None,
            channel_id=payload.channel_id if payload.target_type == "channel" else None,
            title_snapshot=resolved.target.title,
            status="active",
            privacy=payload.privacy,
            current_position=0.0,
            playback_state=resolved.default_playback_state,
            host_last_seen_at=_utcnow(),
        )
        db.add(room)
        db.flush()

        participant = self.participant_repository.create(
            room_id=room.id,
            user_id=user.id,
            is_host=True,
            is_active=True,
            last_seen_at=_utcnow(),
        )
        db.add(participant)
        db.commit()
        refreshed = self.room_repository.get_by_code(db=db, room_code=room.room_code)
        assert refreshed is not None
        return self._build_room_detail_response(db=db, room=refreshed, current_user=user, force_joined=True)

    def join_room(self, *, db: Session, user: User, room_code: str) -> WatchRoomDetailResponse:
        room = self._require_room(db=db, room_code=room_code)
        if room.status != "active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This room is no longer active.")

        participant = self.participant_repository.get_for_user(db=db, room_id=room.id, user_id=user.id)
        if participant is None:
            participant = self.participant_repository.create(
                room_id=room.id,
                user_id=user.id,
                is_host=user.id == room.host_user_id,
                is_active=True,
                last_seen_at=_utcnow(),
            )
            db.add(participant)
        else:
            participant.is_active = True
            participant.left_at = None
            participant.last_seen_at = _utcnow()
        db.commit()
        refreshed = self.room_repository.get_by_code(db=db, room_code=room_code)
        assert refreshed is not None
        return self._build_room_detail_response(db=db, room=refreshed, current_user=user, force_joined=True)

    def get_room_details(self, *, db: Session, user: User, room_code: str) -> WatchRoomDetailResponse:
        room = self._require_room(db=db, room_code=room_code)
        return self._build_room_detail_response(db=db, room=room, current_user=user)

    def leave_room(self, *, db: Session, user: User, room_code: str) -> None:
        room = self._require_room(db=db, room_code=room_code)
        if room.host_user_id == user.id:
            self.end_room(db=db, user=user, room_code=room_code, message="The host ended the room.")
            return

        participant = self._require_active_participant(db=db, room=room, user_id=user.id)
        participant.is_active = False
        participant.left_at = _utcnow()
        participant.last_seen_at = _utcnow()
        db.commit()

    def end_room(self, *, db: Session, user: User, room_code: str, message: str = "The room has ended.") -> None:
        room = self._require_room(db=db, room_code=room_code)
        if room.host_user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the room host can end the room.")
        room.status = "ended"
        room.playback_state = "paused"
        for participant in room.participants:
            participant.is_active = False
            participant.left_at = participant.left_at or _utcnow()
        db.commit()
        self.cancel_host_disconnect(room_code=room.room_code)

    def get_room_for_socket(self, *, db: Session, user: User, room_code: str) -> WatchRoom:
        room = self._require_room(db=db, room_code=room_code)
        if room.status != "active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This room is no longer active.")
        self._require_active_participant(db=db, room=room, user_id=user.id)
        return room

    def touch_participant_presence(self, *, db: Session, room: WatchRoom, user_id: int) -> WatchRoomParticipant:
        participant = self._require_active_participant(db=db, room=room, user_id=user_id)
        participant.last_seen_at = _utcnow()
        if participant.is_host:
            room.host_last_seen_at = participant.last_seen_at
        db.commit()
        db.refresh(participant)
        return participant

    def build_room_state_event(self, *, db: Session, room: WatchRoom, current_user: User | None = None) -> WatchPartyRoomStateEvent:
        detail = self._build_room_detail_response(db=db, room=room, current_user=current_user)
        settings = get_settings()
        return WatchPartyRoomStateEvent(
            type="ROOM_STATE",
            room=detail.room,
            target=detail.target,
            participants=detail.participants,
            recent_messages=detail.recent_messages,
            server_timestamp=_utcnow(),
            drift_threshold_seconds=settings.watch_party_drift_threshold_seconds,
        )

    def build_sync_state_event(self, *, room: WatchRoom) -> WatchPartySyncStateEvent:
        settings = get_settings()
        return WatchPartySyncStateEvent(
            type="SYNC_STATE",
            room_code=room.room_code,
            playback_state=room.playback_state,
            authoritative_position=self._authoritative_position(room),
            server_timestamp=_utcnow(),
            drift_threshold_seconds=settings.watch_party_drift_threshold_seconds,
        )

    def build_user_joined_event(self, *, participant: WatchRoomParticipant) -> WatchPartyUserEvent:
        return WatchPartyUserEvent(
            type="USER_JOINED",
            participant=self._build_participant_read(participant),
            server_timestamp=_utcnow(),
        )

    def build_user_left_event(self, *, participant: WatchRoomParticipant) -> WatchPartyUserEvent:
        return WatchPartyUserEvent(
            type="USER_LEFT",
            participant=self._build_participant_read(participant),
            server_timestamp=_utcnow(),
        )

    def build_room_ended_event(self, *, room_code: str, message: str) -> WatchPartyRoomEndedEvent:
        return WatchPartyRoomEndedEvent(
            type="ROOM_ENDED",
            room_code=room_code,
            message=message,
            server_timestamp=_utcnow(),
        )

    def parse_client_event(self, payload: dict):
        return watch_party_client_event_adapter.validate_python(payload)

    def handle_client_event(self, *, db: Session, room: WatchRoom, user: User, payload: dict):
        event = self.parse_client_event(payload)
        if isinstance(event, WatchPartySyncRequestEvent):
            return "direct", self.build_sync_state_event(room=room)
        if isinstance(event, WatchPartyChatMessageEvent):
            message = self.chat_service.create_message(db=db, room=room, user=user, message_text=event.message)
            refreshed = self.room_repository.get_by_code(db=db, room_code=room.room_code)
            assert refreshed is not None
            created_message = next((item for item in refreshed.messages if item.id == message.id), message)
            return "broadcast", WatchPartyChatBroadcastEvent(
                type="CHAT_MESSAGE",
                message=self._build_message_read(created_message),
                server_timestamp=_utcnow(),
            )
        if isinstance(event, WatchPartyContentChangeEvent):
            participant = self._require_host_participant(db=db, room=room, user_id=user.id)
            resolved = self._resolve_target(
                db=db,
                target_type=event.target_type,
                content_slug=event.content_slug,
                channel_id=event.channel_id,
            )
            room.target_type = event.target_type
            room.content_slug = event.content_slug if event.target_type == "catalog" else None
            room.channel_id = event.channel_id if event.target_type == "channel" else None
            room.title_snapshot = resolved.target.title
            room.current_position = 0.0
            room.playback_state = resolved.default_playback_state
            room.host_last_seen_at = _utcnow()
            db.commit()
            refreshed = self.room_repository.get_by_code(db=db, room_code=room.room_code)
            assert refreshed is not None
            return "broadcast", WatchPartyPlaybackEvent(
                type="CONTENT_CHANGE",
                room_code=refreshed.room_code,
                playback_state=refreshed.playback_state,
                authoritative_position=self._authoritative_position(refreshed),
                server_timestamp=_utcnow(),
                participant=self._build_participant_read(participant),
                target=resolved.target,
            )
        if isinstance(event, (WatchPartyPlayEvent, WatchPartyPauseEvent, WatchPartySeekEvent)):
            participant = self._require_host_participant(db=db, room=room, user_id=user.id)
            if isinstance(event, WatchPartySeekEvent) and not self._room_supports_seek(db=db, room=room):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This room target does not support seek synchronization.")

            room.current_position = float(event.position)
            room.playback_state = (
                "playing"
                if isinstance(event, WatchPartyPlayEvent)
                else "paused"
                if isinstance(event, WatchPartyPauseEvent)
                else room.playback_state
            )
            room.host_last_seen_at = _utcnow()
            db.commit()
            refreshed = self.room_repository.get_by_code(db=db, room_code=room.room_code)
            assert refreshed is not None
            event_type = "PLAY" if isinstance(event, WatchPartyPlayEvent) else "PAUSE" if isinstance(event, WatchPartyPauseEvent) else "SEEK"
            return "broadcast", WatchPartyPlaybackEvent(
                type=event_type,
                room_code=refreshed.room_code,
                playback_state=refreshed.playback_state,
                authoritative_position=self._authoritative_position(refreshed),
                server_timestamp=_utcnow(),
                participant=self._build_participant_read(participant),
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported room event.")

    def cancel_host_disconnect(self, *, room_code: str) -> None:
        task = self._host_disconnect_tasks.pop(room_code, None)
        if task:
            task.cancel()

    def schedule_host_disconnect(self, *, room_code: str) -> None:
        if room_code in self._host_disconnect_tasks:
            return
        settings = get_settings()

        async def _runner() -> None:
            try:
                await asyncio.sleep(settings.watch_party_host_reconnect_grace_seconds)
                if self.connection_manager.is_user_connected(room_code=room_code, user_id=self._host_user_id(room_code=room_code)):
                    return
                if self.session_factory is None:
                    return
                db = self.session_factory()
                try:
                    room = self.room_repository.get_by_code(db=db, room_code=room_code)
                    if room is None or room.status != "active":
                        return
                    room.status = "ended"
                    room.playback_state = "paused"
                    for participant in room.participants:
                        participant.is_active = False
                        participant.left_at = participant.left_at or _utcnow()
                    db.commit()
                finally:
                    db.close()
                event = self.build_room_ended_event(
                    room_code=room_code,
                    message="The host disconnected and the room expired.",
                )
                await self.connection_manager.broadcast(room_code=room_code, payload=event.model_dump(mode="json"))
                await self.connection_manager.close_room(room_code=room_code, code=4002, reason="Room expired.")
            finally:
                self._host_disconnect_tasks.pop(room_code, None)

        self._host_disconnect_tasks[room_code] = asyncio.create_task(_runner())

    def build_error_event(self, *, code: str, message: str) -> WatchPartyErrorEvent:
        return WatchPartyErrorEvent(type="ERROR", code=code, message=message)

    def _host_user_id(self, *, room_code: str) -> int:
        if self.session_factory is None:
            return 0
        db = self.session_factory()
        try:
            room = self.room_repository.get_by_code(db=db, room_code=room_code)
            return room.host_user_id if room else 0
        finally:
            db.close()

    def _build_room_detail_response(
        self,
        *,
        db: Session,
        room: WatchRoom,
        current_user: User | None,
        force_joined: bool = False,
    ) -> WatchRoomDetailResponse:
        participant = None
        if current_user is not None:
            participant = self.participant_repository.get_for_user(db=db, room_id=room.id, user_id=current_user.id)

        resolved = self._resolve_room_target(db=db, room=room)
        messages = self.message_repository.list_recent(
            db=db,
            room_id=room.id,
            limit=get_settings().watch_party_chat_history_limit,
        )
        participants = self.participant_repository.list_active(db=db, room_id=room.id)
        return WatchRoomDetailResponse(
            room=self._build_room_read(room),
            target=resolved.target,
            role="host" if participant and participant.is_host else "participant" if participant and participant.is_active else None,
            joined=force_joined or bool(participant and participant.is_active),
            invite_path=f"#/watch-party/{room.room_code}",
            websocket_url=f"/api/watch-party/ws/{room.room_code}",
            participants=[self._build_participant_read(item) for item in participants],
            recent_messages=[self._build_message_read(item) for item in messages] if force_joined or bool(participant and participant.is_active) else [],
            host_reconnect_grace_seconds=get_settings().watch_party_host_reconnect_grace_seconds,
        )

    def _build_room_read(self, room: WatchRoom) -> WatchRoomRead:
        return WatchRoomRead(
            id=room.id,
            room_code=room.room_code,
            host_user_id=room.host_user_id,
            status=room.status,
            privacy=room.privacy,
            playback_state=room.playback_state,
            current_position=float(room.current_position or 0.0),
            authoritative_position=self._authoritative_position(room),
            created_at=_normalize_datetime(room.created_at) or _utcnow(),
            updated_at=_normalize_datetime(room.updated_at) or _utcnow(),
        )

    def _build_participant_read(self, participant: WatchRoomParticipant) -> WatchRoomParticipantRead:
        profile = participant.user.profile
        display_name = profile.display_name if profile and profile.display_name else participant.user.username
        return WatchRoomParticipantRead(
            user_id=participant.user_id,
            username=participant.user.username,
            display_name=display_name,
            avatar_url=profile.avatar_url if profile else None,
            is_host=participant.is_host,
            joined_at=_normalize_datetime(participant.joined_at) or _utcnow(),
            last_seen_at=_normalize_datetime(participant.last_seen_at),
            is_connected=self.connection_manager.is_user_connected(room_code=participant.room.room_code, user_id=participant.user_id),
        )

    def _build_message_read(self, message: WatchRoomMessage) -> WatchRoomMessageRead:
        profile = message.user.profile
        display_name = profile.display_name if profile and profile.display_name else message.user.username
        return WatchRoomMessageRead(
            id=message.id,
            user_id=message.user_id,
            username=message.user.username,
            display_name=display_name,
            avatar_url=profile.avatar_url if profile else None,
            message_text=message.message_text,
            created_at=_normalize_datetime(message.created_at) or _utcnow(),
        )

    def _require_room(self, *, db: Session, room_code: str) -> WatchRoom:
        room = self.room_repository.get_by_code(db=db, room_code=room_code)
        if room is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch room not found.")
        return room

    def _require_active_participant(self, *, db: Session, room: WatchRoom, user_id: int) -> WatchRoomParticipant:
        participant = self.participant_repository.get_for_user(db=db, room_id=room.id, user_id=user_id)
        if participant is None or not participant.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this room.")
        return participant

    def _require_host_participant(self, *, db: Session, room: WatchRoom, user_id: int) -> WatchRoomParticipant:
        participant = self._require_active_participant(db=db, room=room, user_id=user_id)
        if not participant.is_host:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the room host can control shared playback.")
        return participant

    def _authoritative_position(self, room: WatchRoom) -> float:
        position = float(room.current_position or 0.0)
        if room.playback_state != "playing":
            return max(0.0, position)
        updated_at = _normalize_datetime(room.updated_at) or _utcnow()
        elapsed = max(0.0, (_utcnow() - updated_at).total_seconds())
        return max(0.0, position + elapsed)

    def _generate_room_code(self, *, db: Session) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(20):
            candidate = "".join(secrets.choice(alphabet) for _ in range(6))
            if not self.room_repository.room_code_exists(db=db, room_code=candidate):
                return candidate
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate a room code.")

    def _resolve_target(
        self,
        *,
        db: Session,
        target_type: str,
        content_slug: str | None,
        channel_id: int | None,
    ) -> ResolvedTarget:
        if target_type == "catalog":
            if not content_slug:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="content_slug is required.")
            item = self.catalog_repository.get_by_slug(db=db, slug=content_slug)
            if item is None or not item.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found.")
            playback = self.playback_service.build_response(db=db, item=item, current_user=None)
            if not playback["playback_available"]:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This title is not available for synchronized playback.")
            primary_source = playback["primary_source"]
            subtitle_parts = [item.content_type.upper()]
            if item.release_date:
                subtitle_parts.append(str(item.release_date.year))
            return ResolvedTarget(
                target=WatchRoomTargetRead(
                    target_type="catalog",
                    content_slug=item.slug,
                    title=item.title,
                    subtitle=" • ".join(subtitle_parts),
                    poster_url=item.poster_url,
                    backdrop_url=item.backdrop_url,
                    playback_supported=True,
                ),
                playback_supported=True,
                supports_seek=bool(primary_source["capabilities"]["can_seek"]) if primary_source else False,
                default_playback_state="paused",
            )

        if not channel_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="channel_id is required.")
        channel = self.channel_repository.get_by_id(db=db, channel_id=channel_id)
        if channel is None or not channel.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found.")
        live_payload = self.live_tv_service.build_channel_live_read(channel)
        if live_payload.playback.type == "unavailable":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This live channel is not available for synchronized playback.")
        title = live_payload.current_program.title if live_payload.current_program else live_payload.live_title or channel.name
        subtitle = live_payload.name if title != live_payload.name else live_payload.source_type.upper()
        return ResolvedTarget(
            target=WatchRoomTargetRead(
                target_type="channel",
                channel_id=channel.id,
                title=title,
                subtitle=subtitle,
                poster_url=channel.logo_url,
                backdrop_url=channel.thumbnail_url or channel.logo_url,
                live_status=live_payload.live_status,
                playback_supported=True,
            ),
            playback_supported=True,
            supports_seek=False,
            default_playback_state="playing",
        )

    def _resolve_room_target(self, *, db: Session, room: WatchRoom) -> ResolvedTarget:
        try:
            return self._resolve_target(
                db=db,
                target_type=room.target_type,
                content_slug=room.content_slug,
                channel_id=room.channel_id,
            )
        except HTTPException:
            return ResolvedTarget(
                target=WatchRoomTargetRead(
                    target_type=room.target_type,
                    content_slug=room.content_slug,
                    channel_id=room.channel_id,
                    title=room.title_snapshot or "Unavailable content",
                    subtitle=None,
                    playback_supported=False,
                ),
                playback_supported=False,
                supports_seek=False,
                default_playback_state="paused",
            )

    def _room_supports_seek(self, *, db: Session, room: WatchRoom) -> bool:
        return self._resolve_room_target(db=db, room=room).supports_seek
