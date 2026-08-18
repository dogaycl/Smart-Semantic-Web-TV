from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class WatchRoom(Base):
    __tablename__ = "watch_rooms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    room_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    host_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    content_slug: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), nullable=True, index=True)
    title_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    privacy: Mapped[str] = mapped_column(String(24), nullable=False, default="invite_only", server_default="invite_only")
    current_position: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    playback_state: Mapped[str] = mapped_column(String(24), nullable=False, default="paused", server_default="paused")
    host_last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    host_user = relationship("User", back_populates="hosted_watch_rooms")
    channel = relationship("Channel", back_populates="watch_rooms")
    participants = relationship(
        "WatchRoomParticipant",
        back_populates="room",
        cascade="all, delete-orphan",
        order_by="WatchRoomParticipant.joined_at.asc()",
    )
    messages = relationship(
        "WatchRoomMessage",
        back_populates="room",
        cascade="all, delete-orphan",
        order_by="WatchRoomMessage.created_at.asc()",
    )
