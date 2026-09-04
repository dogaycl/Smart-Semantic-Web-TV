"""Add is_pinned flag to catalog items

Pinned catalog items (bulk TMDB import, wired-up playable titles) are exempt from the
bucket-sync deactivation sweep so a scheduled catalog reconciliation no longer wipes
curator-added movies.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260902_0013"
down_revision: str | None = "20260902_0012"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "catalog_items",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("catalog_items", "is_pinned")
