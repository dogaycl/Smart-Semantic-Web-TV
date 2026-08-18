from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class WatchRoomParticipant(Base):
    __tablename__ = "watch_room_participants"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_watch_room_participants_room_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("watch_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_host: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="1")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    room = relationship("WatchRoom", back_populates="participants")
    user = relationship("User", back_populates="watch_room_participants")
