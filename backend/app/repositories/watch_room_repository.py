from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.user import User
from app.models.watch_room import WatchRoom
from app.models.watch_room_message import WatchRoomMessage
from app.models.watch_room_participant import WatchRoomParticipant


ROOM_EAGER_LOADS = (
    selectinload(WatchRoom.host_user).selectinload(User.profile),
    selectinload(WatchRoom.participants).selectinload(WatchRoomParticipant.user).selectinload(User.profile),
    selectinload(WatchRoom.messages).selectinload(WatchRoomMessage.user).selectinload(User.profile),
    selectinload(WatchRoom.channel),
)


class WatchRoomRepository:
    def get_by_code(self, *, db: Session, room_code: str) -> WatchRoom | None:
        statement = (
            select(WatchRoom)
            .options(*ROOM_EAGER_LOADS)
            .where(WatchRoom.room_code == room_code)
        )
        return db.scalar(statement)

    def create(self, **kwargs) -> WatchRoom:
        return WatchRoom(**kwargs)

    def room_code_exists(self, *, db: Session, room_code: str) -> bool:
        statement = select(func.count(WatchRoom.id)).where(WatchRoom.room_code == room_code)
        return bool(db.scalar(statement))


class WatchRoomParticipantRepository:
    def get_for_user(self, *, db: Session, room_id: int, user_id: int) -> WatchRoomParticipant | None:
        statement = (
            select(WatchRoomParticipant)
            .options(selectinload(WatchRoomParticipant.user).selectinload(User.profile))
            .where(
                WatchRoomParticipant.room_id == room_id,
                WatchRoomParticipant.user_id == user_id,
            )
        )
        return db.scalar(statement)

    def list_active(self, *, db: Session, room_id: int) -> list[WatchRoomParticipant]:
        statement = (
            select(WatchRoomParticipant)
            .options(selectinload(WatchRoomParticipant.user).selectinload(User.profile))
            .where(
                WatchRoomParticipant.room_id == room_id,
                WatchRoomParticipant.is_active.is_(True),
            )
            .order_by(WatchRoomParticipant.is_host.desc(), WatchRoomParticipant.joined_at.asc())
        )
        return list(db.scalars(statement).all())

    def create(self, **kwargs) -> WatchRoomParticipant:
        return WatchRoomParticipant(**kwargs)


class WatchRoomMessageRepository:
    def list_recent(self, *, db: Session, room_id: int, limit: int = 40) -> list[WatchRoomMessage]:
        statement = (
            select(WatchRoomMessage)
            .options(selectinload(WatchRoomMessage.user).selectinload(User.profile))
            .where(WatchRoomMessage.room_id == room_id)
            .order_by(WatchRoomMessage.created_at.desc(), WatchRoomMessage.id.desc())
            .limit(limit)
        )
        messages = list(db.scalars(statement).all())
        messages.reverse()
        return messages

    def create(self, **kwargs) -> WatchRoomMessage:
        return WatchRoomMessage(**kwargs)
