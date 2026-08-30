from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ViewingPlan(Base):
    __tablename__ = "viewing_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    available_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    available_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    max_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    include_live: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="1")
    include_vod: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="1")
    preferred_categories: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    preference_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    profile_summary: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    summary: Mapped[str] = mapped_column(Text(), nullable=False)
    generation_source: Mapped[str] = mapped_column(String(24), nullable=False, default="fallback", server_default="fallback")
    llm_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    llm_repair_applied: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="0")
    # `is_accepted` is the flag a partial unique index uses to enforce one active plan per
    # (user, plan_date). `status` records *why* a plan is not accepted: "draft" was never
    # accepted, "superseded" was accepted and later replaced for the same date. Superseded
    # plans are kept as history rather than deleted, so the two are maintained together.
    is_accepted: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="0")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="draft", server_default="draft"
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_accepted: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="0", index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    user = relationship("User", back_populates="viewing_plans")
    items = relationship(
        "ViewingPlanItem",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ViewingPlanItem.position.asc()",
    )
