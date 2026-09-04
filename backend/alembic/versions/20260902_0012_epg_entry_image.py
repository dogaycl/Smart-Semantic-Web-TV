"""Add programme image URL to EPG entries"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260902_0012"
down_revision: str | None = "20260831_0011"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("epg_entries", sa.Column("image_url", sa.String(length=600), nullable=True))


def downgrade() -> None:
    op.drop_column("epg_entries", "image_url")
