"""Add viewing planner persistence tables"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260815_0006"
down_revision: str | None = "20260815_0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "viewing_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("available_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("include_live", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_vod", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("preferred_categories", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("preference_text", sa.Text(), nullable=True),
        sa.Column("profile_summary", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("generation_source", sa.String(length=24), nullable=False, server_default="fallback"),
        sa.Column("llm_model", sa.String(length=80), nullable=True),
        sa.Column("llm_repair_applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_viewing_plans_id", "viewing_plans", ["id"], unique=False)
    op.create_index("ix_viewing_plans_user_id", "viewing_plans", ["user_id"], unique=False)
    op.create_index("ix_viewing_plans_plan_date", "viewing_plans", ["plan_date"], unique=False)
    op.create_index("ix_viewing_plans_available_start", "viewing_plans", ["available_start"], unique=False)
    op.create_index("ix_viewing_plans_available_end", "viewing_plans", ["available_end"], unique=False)

    op.create_table(
        "viewing_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("viewing_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("result_type", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("epg_entry_id", sa.Integer(), sa.ForeignKey("epg_entries.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_label", sa.String(length=120), nullable=False),
        sa.Column("genres", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("poster_url", sa.String(length=500), nullable=True),
        sa.Column("backdrop_url", sa.String(length=500), nullable=True),
        sa.Column("content_slug", sa.String(length=180), nullable=True),
        sa.Column("channel_slug", sa.String(length=100), nullable=True),
        sa.Column("channel_name", sa.String(length=150), nullable=True),
        sa.Column("channel_logo_url", sa.String(length=500), nullable=True),
        sa.Column("channel_source_type", sa.String(length=16), nullable=True),
        sa.Column("runtime_minutes", sa.Integer(), nullable=True),
        sa.Column("runtime_display", sa.String(length=64), nullable=False),
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("availability_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("availability_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recommendation_score", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("plan_id", "position", name="uq_viewing_plan_items_plan_position"),
    )
    op.create_index("ix_viewing_plan_items_id", "viewing_plan_items", ["id"], unique=False)
    op.create_index("ix_viewing_plan_items_plan_id", "viewing_plan_items", ["plan_id"], unique=False)
    op.create_index("ix_viewing_plan_items_candidate_id", "viewing_plan_items", ["candidate_id"], unique=False)
    op.create_index("ix_viewing_plan_items_planned_start", "viewing_plan_items", ["planned_start"], unique=False)
    op.create_index("ix_viewing_plan_items_planned_end", "viewing_plan_items", ["planned_end"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_viewing_plan_items_planned_end", table_name="viewing_plan_items")
    op.drop_index("ix_viewing_plan_items_planned_start", table_name="viewing_plan_items")
    op.drop_index("ix_viewing_plan_items_candidate_id", table_name="viewing_plan_items")
    op.drop_index("ix_viewing_plan_items_plan_id", table_name="viewing_plan_items")
    op.drop_index("ix_viewing_plan_items_id", table_name="viewing_plan_items")
    op.drop_table("viewing_plan_items")

    op.drop_index("ix_viewing_plans_available_end", table_name="viewing_plans")
    op.drop_index("ix_viewing_plans_available_start", table_name="viewing_plans")
    op.drop_index("ix_viewing_plans_plan_date", table_name="viewing_plans")
    op.drop_index("ix_viewing_plans_user_id", table_name="viewing_plans")
    op.drop_index("ix_viewing_plans_id", table_name="viewing_plans")
    op.drop_table("viewing_plans")
