from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, TypeAdapter, model_validator


RoomTargetType = Literal["catalog", "channel"]
RoomStatus = Literal["active", "ended"]
RoomPrivacy = Literal["invite_only", "private"]
RoomPlaybackState = Literal["idle", "playing", "paused", "ended"]
RoomRole = Literal["host", "participant"]
WatchPartyEventType = Literal[
    "JOIN_ROOM",
    "ROOM_STATE",
    "USER_JOINED",
    "USER_LEFT",
    "PLAY",
    "PAUSE",
    "SEEK",
    "CONTENT_CHANGE",
    "CHAT_MESSAGE",
    "SYNC_REQUEST",
    "SYNC_STATE",
    "ROOM_ENDED",
    "ERROR",
]


class WatchRoomCreateRequest(BaseModel):
    target_type: RoomTargetType
    content_slug: str | None = Field(default=None, min_length=1, max_length=180)
    channel_id: int | None = Field(default=None, ge=1)
    privacy: RoomPrivacy = "invite_only"

    @model_validator(mode="after")
    def validate_target(self) -> "WatchRoomCreateRequest":
        if self.target_type == "catalog" and not self.content_slug:
            raise ValueError("content_slug is required when target_type is catalog.")
        if self.target_type == "channel" and not self.channel_id:
            raise ValueError("channel_id is required when target_type is channel.")
        return self


class WatchRoomTargetRead(BaseModel):
    target_type: RoomTargetType
    content_slug: str | None = None
    channel_id: int | None = None
    title: str
    subtitle: str | None = None
    poster_url: HttpUrl | None = None
    backdrop_url: HttpUrl | None = None
    live_status: str | None = None
    playback_supported: bool


class WatchRoomParticipantRead(BaseModel):
    user_id: int
    username: str
    display_name: str
    avatar_url: str | None = None
    is_host: bool
    joined_at: datetime
    last_seen_at: datetime | None = None
    is_connected: bool


class WatchRoomMessageRead(BaseModel):
    id: int
    user_id: int
    username: str
    display_name: str
    avatar_url: str | None = None
    message_text: str
    created_at: datetime


class WatchRoomRead(BaseModel):
    id: int
    room_code: str
    host_user_id: int
    status: RoomStatus
    privacy: RoomPrivacy
    playback_state: RoomPlaybackState
    current_position: float
    authoritative_position: float
    created_at: datetime
    updated_at: datetime


class WatchRoomDetailResponse(BaseModel):
    room: WatchRoomRead
    target: WatchRoomTargetRead
    role: RoomRole | None = None
    joined: bool
    invite_path: str
    websocket_url: str
    participants: list[WatchRoomParticipantRead]
    recent_messages: list[WatchRoomMessageRead]
    host_reconnect_grace_seconds: int


class WatchPartyEventBase(BaseModel):
    type: WatchPartyEventType


class WatchPartySyncRequestEvent(WatchPartyEventBase):
    type: Literal["SYNC_REQUEST"]


class WatchPartyPlayEvent(WatchPartyEventBase):
    type: Literal["PLAY"]
    position: float = Field(ge=0)


class WatchPartyPauseEvent(WatchPartyEventBase):
    type: Literal["PAUSE"]
    position: float = Field(ge=0)


class WatchPartySeekEvent(WatchPartyEventBase):
    type: Literal["SEEK"]
    position: float = Field(ge=0)


class WatchPartyChatMessageEvent(WatchPartyEventBase):
    type: Literal["CHAT_MESSAGE"]
    message: str = Field(min_length=1, max_length=400)


class WatchPartyContentChangeEvent(WatchPartyEventBase):
    type: Literal["CONTENT_CHANGE"]
    target_type: RoomTargetType
    content_slug: str | None = Field(default=None, min_length=1, max_length=180)
    channel_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_target(self) -> "WatchPartyContentChangeEvent":
        if self.target_type == "catalog" and not self.content_slug:
            raise ValueError("content_slug is required when target_type is catalog.")
        if self.target_type == "channel" and not self.channel_id:
            raise ValueError("channel_id is required when target_type is channel.")
        return self


WatchPartyClientEvent = Annotated[
    WatchPartySyncRequestEvent
    | WatchPartyPlayEvent
    | WatchPartyPauseEvent
    | WatchPartySeekEvent
    | WatchPartyChatMessageEvent
    | WatchPartyContentChangeEvent,
    Field(discriminator="type"),
]

watch_party_client_event_adapter = TypeAdapter(WatchPartyClientEvent)


class WatchPartyRoomStateEvent(WatchPartyEventBase):
    type: Literal["ROOM_STATE"]
    room: WatchRoomRead
    target: WatchRoomTargetRead
    participants: list[WatchRoomParticipantRead]
    recent_messages: list[WatchRoomMessageRead] = Field(default_factory=list)
    server_timestamp: datetime
    drift_threshold_seconds: float


class WatchPartyUserEvent(WatchPartyEventBase):
    participant: WatchRoomParticipantRead
    server_timestamp: datetime


class WatchPartySyncStateEvent(WatchPartyEventBase):
    type: Literal["SYNC_STATE"]
    room_code: str
    playback_state: RoomPlaybackState
    authoritative_position: float
    server_timestamp: datetime
    drift_threshold_seconds: float


class WatchPartyPlaybackEvent(WatchPartyEventBase):
    type: Literal["PLAY", "PAUSE", "SEEK", "CONTENT_CHANGE"]
    room_code: str
    playback_state: RoomPlaybackState
    authoritative_position: float
    server_timestamp: datetime
    participant: WatchRoomParticipantRead | None = None
    target: WatchRoomTargetRead | None = None


class WatchPartyChatBroadcastEvent(WatchPartyEventBase):
    type: Literal["CHAT_MESSAGE"]
    message: WatchRoomMessageRead
    server_timestamp: datetime


class WatchPartyRoomEndedEvent(WatchPartyEventBase):
    type: Literal["ROOM_ENDED"]
    room_code: str
    message: str
    server_timestamp: datetime


class WatchPartyErrorEvent(WatchPartyEventBase):
    type: Literal["ERROR"]
    code: str
    message: str
