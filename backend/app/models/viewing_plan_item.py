from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ViewingPlanItem(Base):
    __tablename__ = "viewing_plan_items"
    __table_args__ = (
        UniqueConstraint("plan_id", "position", name="uq_viewing_plan_items_plan_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("viewing_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    result_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    catalog_item_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True)
    epg_entry_id: Mapped[int | None] = mapped_column(ForeignKey("epg_entries.id", ondelete="SET NULL"), nullable=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    category_label: Mapped[str] = mapped_column(String(120), nullable=False)
    genres: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    backdrop_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_slug: Mapped[str | None] = mapped_column(String(180), nullable=True)
    channel_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    channel_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    channel_logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    channel_source_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runtime_display: Mapped[str] = mapped_column(String(64), nullable=False)
    planned_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    planned_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    availability_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    availability_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recommendation_score: Mapped[float | None] = mapped_column(Float(), nullable=True)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    plan = relationship("ViewingPlan", back_populates="items")
